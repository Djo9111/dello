import uuid
from datetime import date

import pytest

from app.core.security import hash_password
from app.modules.claims import service
from app.modules.claims.exceptions import (
    ClaimAlreadyExistsError,
    ClaimAlreadyResolvedError,
    ClaimNotAllowedError,
    ClaimNotFoundError,
    WrongVerificationAnswerError,
)
from app.modules.claims.models import ClaimStatus
from app.modules.claims.verification import hash_answer
from app.modules.reports import service as reports_service
from app.modules.reports.models import ReportStatus
from app.modules.reports.schemas import ReportCreate
from app.modules.users.models import User

ANSWER = "12 juin 1995"


def _user(db, phone: str, name="Moussa Fall") -> User:
    user = User(
        phone_number=phone,
        full_name=name,
        hashed_password=hash_password("Tamarin-Soleil-9"),
    )
    db.add(user)
    db.commit()
    return user


def _found_report(db, finder, *, with_question=True):
    payload = ReportCreate(
        kind="found",
        document_type="cni",
        document_number="1234567890123",
        owner_name="Modienne GUISSE",
        region="Dakar",
        commune="Keur Massar",
        occurred_on=date(2026, 9, 20),
    )
    report = reports_service.create_report(db, finder, payload)

    if with_question:
        report.verification_question = "Date de naissance sur la carte ?"
        report.verification_answer_hash = hash_answer(ANSWER)
        db.commit()

    return report


# ---------------------------------------------------------------------------
# Création et vérification automatique
# ---------------------------------------------------------------------------


def test_right_answer_verifies_immediately(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)

    claim = service.create_claim(db_session, report, owner, answer="12 JUIN 1995")

    assert claim.status is ClaimStatus.VERIFIED
    assert claim.resolved_at is not None
    db_session.refresh(report)
    assert report.status is ReportStatus.MATCHED


def test_wrong_answer_waits_for_the_finder(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)

    claim = service.create_claim(db_session, report, owner, answer="1 janvier 2000")

    assert claim.status is ClaimStatus.PENDING
    assert claim.answer_attempts == 1


def test_report_without_question_waits_for_the_finder(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder, with_question=False)

    claim = service.create_claim(db_session, report, owner, message="C'est ma carte")

    assert claim.status is ClaimStatus.PENDING
    assert claim.message == "C'est ma carte"


def test_second_attempt_can_succeed(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    claim = service.create_claim(db_session, report, owner, answer="faux")

    verified = service.answer_verification(db_session, claim, ANSWER)

    assert verified.status is ClaimStatus.VERIFIED


def test_attempts_are_limited_then_human_decides(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    claim = service.create_claim(db_session, report, owner, answer="faux")

    for _ in range(service.MAX_ANSWER_ATTEMPTS):
        with pytest.raises(WrongVerificationAnswerError):
            service.answer_verification(db_session, claim, "encore faux")

    # Même la bonne réponse ne passe plus automatiquement
    with pytest.raises(WrongVerificationAnswerError):
        service.answer_verification(db_session, claim, ANSWER)

    # Mais la demande reste ouverte : le déclarant peut toujours accepter
    assert claim.status is ClaimStatus.PENDING
    assert service.approve_claim(db_session, claim).status is ClaimStatus.VERIFIED


# ---------------------------------------------------------------------------
# Règles d'accès
# ---------------------------------------------------------------------------


def test_cannot_claim_own_report(db_session):
    finder = _user(db_session, "+221781112233")
    report = _found_report(db_session, finder)

    with pytest.raises(ClaimNotAllowedError):
        service.create_claim(db_session, report, finder)


def test_cannot_claim_anonymized_report(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    report.user_id = None
    db_session.commit()

    with pytest.raises(ClaimNotAllowedError):
        service.create_claim(db_session, report, owner)


def test_cannot_claim_closed_report(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    service.close_report(db_session, report)

    with pytest.raises(ClaimNotAllowedError):
        service.create_claim(db_session, report, owner)


def test_only_one_claim_per_person(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    service.create_claim(db_session, report, owner, answer="faux")

    with pytest.raises(ClaimAlreadyExistsError):
        service.create_claim(db_session, report, owner, answer="faux")


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


def test_contacts_are_hidden_while_pending(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder, with_question=False)
    claim = service.create_claim(db_session, report, owner)

    with pytest.raises(ClaimNotFoundError):
        service.get_contact(db_session, claim, owner)


def test_both_parties_get_the_contact_once_verified(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    claim = service.create_claim(db_session, report, owner, answer=ANSWER)

    assert service.get_contact(db_session, claim, owner).phone_number == "+221781112233"
    assert service.get_contact(db_session, claim, finder).phone_number == "+221771234567"


def test_a_stranger_gets_no_contact(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    stranger = _user(db_session, "+221701112233", name="Ndeye Sow")
    report = _found_report(db_session, finder)
    claim = service.create_claim(db_session, report, owner, answer=ANSWER)

    with pytest.raises(ClaimNotFoundError):
        service.get_contact(db_session, claim, stranger)


def test_withdrawing_cuts_the_contact(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder)
    claim = service.create_claim(db_session, report, owner, answer=ANSWER)

    service.withdraw_claim(db_session, claim)

    with pytest.raises(ClaimNotFoundError):
        service.get_contact(db_session, claim, owner)


# ---------------------------------------------------------------------------
# Décisions et clôture
# ---------------------------------------------------------------------------


def test_rejected_claim_cannot_be_approved_afterwards(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder, with_question=False)
    claim = service.create_claim(db_session, report, owner)

    service.reject_claim(db_session, claim)

    with pytest.raises(ClaimAlreadyResolvedError):
        service.approve_claim(db_session, claim)


def test_closing_report_rejects_pending_claims(db_session):
    finder = _user(db_session, "+221781112233")
    awa = _user(db_session, "+221771234567", name="Awa Diop")
    ndeye = _user(db_session, "+221701112233", name="Ndeye Sow")
    report = _found_report(db_session, finder)

    verified = service.create_claim(db_session, report, awa, answer=ANSWER)
    pending = service.create_claim(db_session, report, ndeye, answer="faux")

    service.close_report(db_session, report)

    db_session.refresh(verified)
    db_session.refresh(pending)
    assert report.status is ReportStatus.CLOSED
    assert verified.status is ClaimStatus.VERIFIED
    assert pending.status is ClaimStatus.REJECTED


def test_claim_visibility(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    stranger = _user(db_session, "+221701112233", name="Ndeye Sow")
    report = _found_report(db_session, finder, with_question=False)
    claim = service.create_claim(db_session, report, owner)

    assert service.get_claim_for_participant(db_session, claim.id, owner).id == claim.id
    assert service.get_claim_for_participant(db_session, claim.id, finder).id == claim.id

    with pytest.raises(ClaimNotFoundError):
        service.get_claim_for_participant(db_session, claim.id, stranger)
    with pytest.raises(ClaimNotFoundError):
        service.get_claim_as_report_owner(db_session, claim.id, owner)
    with pytest.raises(ClaimNotFoundError):
        service.get_claim_as_claimant(db_session, claim.id, finder)


def test_unknown_claim(db_session):
    user = _user(db_session, "+221781112233")

    with pytest.raises(ClaimNotFoundError):
        service.get_claim_for_participant(db_session, uuid.uuid4(), user)


def test_lists_are_separated(db_session):
    finder = _user(db_session, "+221781112233")
    owner = _user(db_session, "+221771234567", name="Awa Diop")
    report = _found_report(db_session, finder, with_question=False)
    claim = service.create_claim(db_session, report, owner)

    assert [c.id for c in service.list_my_claims(db_session, owner)] == [claim.id]
    assert service.list_my_claims(db_session, finder) == []
    assert [c.id for c in service.list_claims_on_my_reports(db_session, finder)] == [claim.id]
    assert service.list_claims_on_my_reports(db_session, owner) == []