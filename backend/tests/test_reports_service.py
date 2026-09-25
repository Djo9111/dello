import uuid
from datetime import date

import pytest

from app.core.security import hash_document_number, hash_password
from app.modules.reports import service
from app.modules.reports.exceptions import ReportNotFoundError
from app.modules.reports.models import DocumentType, ReportKind, ReportStatus
from app.modules.reports.schemas import ReportCreate, ReportUpdate
from app.modules.users.models import User

NUMBER = "1234567890123"


def _user(db, phone="+221771234567") -> User:
    user = User(
        phone_number=phone,
        full_name="Awa Diop",
        hashed_password=hash_password("Tamarin-Soleil-9"),
    )
    db.add(user)
    db.commit()
    return user


def _payload(**overrides) -> ReportCreate:
    data = {
        "kind": "lost",
        "document_type": "cni",
        "document_number": NUMBER,
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
        "place_detail": "pres du marche",
        "occurred_on": date(2026, 9, 20),
    }
    data.update(overrides)
    return ReportCreate(**data)


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def test_create_hashes_number_and_masks_name(db_session):
    user = _user(db_session)

    report = service.create_report(db_session, user, _payload())

    assert report.document_number_hmac == hash_document_number("cni", NUMBER)
    assert report.owner_name_masked == "Mod... G..."
    assert report.status is ReportStatus.OPEN
    assert report.is_published is True


def test_create_without_number_or_name(db_session):
    user = _user(db_session)

    report = service.create_report(
        db_session, user, _payload(document_number=None, owner_name=None)
    )

    assert report.document_number_hmac is None
    assert report.owner_name_masked is None


def test_same_number_gives_same_hmac_whatever_the_formatting(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    lost = service.create_report(db_session, awa, _payload(document_number="1 234-567 890 123"))
    found = service.create_report(
        db_session, moussa, _payload(kind="found", document_number=NUMBER)
    )

    assert lost.document_number_hmac == found.document_number_hmac


def test_different_document_types_do_not_collide(db_session):
    user = _user(db_session)

    cni = service.create_report(db_session, user, _payload(document_type="cni"))
    permis = service.create_report(db_session, user, _payload(document_type="permis"))

    assert cni.document_number_hmac != permis.document_number_hmac


# ---------------------------------------------------------------------------
# Rapprochement
# ---------------------------------------------------------------------------


def test_matching_finds_opposite_kind(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    lost = service.create_report(db_session, awa, _payload(kind="lost"))
    found = service.create_report(db_session, moussa, _payload(kind="found"))

    assert [r.id for r in service.find_potential_matches(db_session, lost)] == [found.id]
    assert [r.id for r in service.find_potential_matches(db_session, found)] == [lost.id]


def test_matching_ignores_same_kind(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    first = service.create_report(db_session, awa, _payload(kind="lost"))
    service.create_report(db_session, moussa, _payload(kind="lost"))

    assert service.find_potential_matches(db_session, first) == []


def test_matching_ignores_other_numbers(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    lost = service.create_report(db_session, awa, _payload(kind="lost"))
    service.create_report(
        db_session, moussa, _payload(kind="found", document_number="9999999999999")
    )

    assert service.find_potential_matches(db_session, lost) == []


def test_matching_ignores_closed_reports(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    lost = service.create_report(db_session, awa, _payload(kind="lost"))
    found = service.create_report(db_session, moussa, _payload(kind="found"))
    found.status = ReportStatus.CLOSED
    db_session.commit()

    assert service.find_potential_matches(db_session, lost) == []


def test_report_without_number_has_no_match(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    lost = service.create_report(db_session, awa, _payload(document_number=None))
    service.create_report(db_session, moussa, _payload(kind="found"))

    assert service.find_potential_matches(db_session, lost) == []


# ---------------------------------------------------------------------------
# Accès
# ---------------------------------------------------------------------------


def test_owner_can_read_own_report(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())

    assert service.get_own_report(db_session, report.id, user).id == report.id


def test_other_user_cannot_read_it_as_owner(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")
    report = service.create_report(db_session, awa, _payload())

    with pytest.raises(ReportNotFoundError):
        service.get_own_report(db_session, report.id, moussa)


def test_unknown_report_raises_the_same_error(db_session):
    user = _user(db_session)

    with pytest.raises(ReportNotFoundError):
        service.get_own_report(db_session, uuid.uuid4(), user)


def test_unpublished_report_is_not_public(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())
    report.is_published = False
    db_session.commit()

    with pytest.raises(ReportNotFoundError):
        service.get_public_report(db_session, report.id)


def test_closed_report_is_not_public(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())
    report.status = ReportStatus.CLOSED
    db_session.commit()

    with pytest.raises(ReportNotFoundError):
        service.get_public_report(db_session, report.id)


def test_anonymized_report_has_no_owner(db_session):
    awa = _user(db_session)
    report = service.create_report(db_session, awa, _payload(kind="found"))
    report.user_id = None
    db_session.commit()

    with pytest.raises(ReportNotFoundError):
        service.get_own_report(db_session, report.id, awa)

    assert service.get_public_report(db_session, report.id).id == report.id


# ---------------------------------------------------------------------------
# Listes
# ---------------------------------------------------------------------------


def test_public_list_excludes_hidden_reports(db_session):
    user = _user(db_session)
    visible = service.create_report(db_session, user, _payload())
    hidden = service.create_report(db_session, user, _payload(document_number=None))
    hidden.is_published = False
    db_session.commit()

    listed = service.list_public_reports(db_session)

    assert [r.id for r in listed] == [visible.id]


def test_public_list_filters(db_session):
    user = _user(db_session)
    service.create_report(db_session, user, _payload(kind="lost", document_type="cni"))
    found = service.create_report(db_session, user, _payload(kind="found", document_type="permis", region="Thies"))

    assert [r.id for r in service.list_public_reports(db_session, kind=ReportKind.FOUND)] == [found.id]
    assert [r.id for r in service.list_public_reports(db_session, document_type=DocumentType.PERMIS)] == [found.id]
    assert [r.id for r in service.list_public_reports(db_session, region="Thies")] == [found.id]


def test_page_size_is_capped(db_session):
    user = _user(db_session)
    for _ in range(3):
        service.create_report(db_session, user, _payload(document_number=None))

    assert len(service.list_public_reports(db_session, limit=1000)) == 3
    assert len(service.list_public_reports(db_session, limit=2)) == 2
    assert len(service.list_public_reports(db_session, limit=2, offset=2)) == 1


def test_own_list_shows_only_my_reports(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")
    mine = service.create_report(db_session, awa, _payload())
    service.create_report(db_session, moussa, _payload())

    assert [r.id for r in service.list_own_reports(db_session, awa)] == [mine.id]


# ---------------------------------------------------------------------------
# Modification et suppression
# ---------------------------------------------------------------------------


def test_update_changes_only_sent_fields(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())

    service.update_report(db_session, report, ReportUpdate(commune="Pikine"))

    assert report.commune == "Pikine"
    assert report.place_detail == "pres du marche"
    assert report.is_published is True


def test_unpublishing_removes_from_public_list(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())

    service.update_report(db_session, report, ReportUpdate(is_published=False))

    assert service.list_public_reports(db_session) == []


def test_delete_removes_the_report(db_session):
    user = _user(db_session)
    report = service.create_report(db_session, user, _payload())

    service.delete_report(db_session, report)

    with pytest.raises(ReportNotFoundError):
        service.get_own_report(db_session, report.id, user)