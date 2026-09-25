import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_document_number, hash_password
from app.modules.reports.models import (
    DocumentType,
    Report,
    ReportImage,
    ReportKind,
    ReportStatus,
)
from app.modules.users.models import User


def _user(db, phone="+221771234567") -> User:
    user = User(
        phone_number=phone,
        full_name="Awa Diop",
        hashed_password=hash_password("Tamarin-Soleil-9"),
    )
    db.add(user)
    db.commit()
    return user


def _report(db, user, kind=ReportKind.LOST, number="1234567890123") -> Report:
    report = Report(
        user_id=user.id,
        kind=kind,
        document_type=DocumentType.CNI,
        document_number_hmac=hash_document_number("cni", number),
        owner_name_masked="Awa D...",
        region="Dakar",
        commune="Keur Massar",
        occurred_on=date(2026, 9, 20),
    )
    db.add(report)
    db.commit()
    return report


def test_defaults(db_session):
    report = _report(db_session, _user(db_session))

    assert report.status == ReportStatus.OPEN
    assert report.is_published is True
    assert len(report.document_number_hmac) == 64


def test_report_without_document_number(db_session):
    user = _user(db_session)
    report = Report(
        user_id=user.id,
        kind=ReportKind.FOUND,
        document_type=DocumentType.AUTRE,
        region="Thies",
    )
    db_session.add(report)
    db_session.commit()

    assert report.document_number_hmac is None


def test_invalid_hmac_length_is_rejected(db_session):
    user = _user(db_session)
    report = Report(
        user_id=user.id,
        kind=ReportKind.LOST,
        document_type=DocumentType.CNI,
        document_number_hmac="trop-court",
        region="Dakar",
    )
    db_session.add(report)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_kind_is_rejected(db_session):
    user = _user(db_session)

    # execute() envoie l'INSERT tout de suite, l'erreur arrive ici et non au commit
    with pytest.raises(IntegrityError):
        db_session.execute(
            Report.__table__.insert().values(
                id=uuid.uuid4(),
                user_id=user.id,
                kind="peut-etre",
                document_type="cni",
                region="Dakar",
                status="open",
                is_published=True,
            )
        )

    db_session.rollback()


def test_matching_by_hmac(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    _report(db_session, awa, kind=ReportKind.LOST, number="1 234 567 890 123")
    found = _report(db_session, moussa, kind=ReportKind.FOUND, number="1234567890123")

    # La requete du moteur de rapprochement
    candidates = db_session.scalars(
        select(Report).where(
            Report.kind == ReportKind.FOUND,
            Report.document_number_hmac == hash_document_number("cni", "1234567890123"),
        )
    ).all()

    assert [report.id for report in candidates] == [found.id]


def test_images_are_deleted_with_report(db_session):
    report = _report(db_session, _user(db_session))
    db_session.add(
        ReportImage(
            report_id=report.id,
            storage_path="reports/photo-1.jpg",
            content_type="image/jpeg",
            size_bytes=124000,
        )
    )
    db_session.commit()

    db_session.delete(report)
    db_session.commit()

    assert db_session.scalars(select(ReportImage)).all() == []


def test_image_is_private_by_default(db_session):
    report = _report(db_session, _user(db_session))
    image = ReportImage(
        report_id=report.id,
        storage_path="reports/photo-2.jpg",
        content_type="image/jpeg",
        size_bytes=98000,
    )
    db_session.add(image)
    db_session.commit()

    assert image.is_public is False


def test_storage_path_is_unique(db_session):
    report = _report(db_session, _user(db_session))
    for _ in range(2):
        db_session.add(
            ReportImage(
                report_id=report.id,
                storage_path="reports/doublon.jpg",
                content_type="image/jpeg",
                size_bytes=1000,
            )
        )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()