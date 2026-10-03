from sqlalchemy import select

from app.core.config import settings
from app.modules.notifications.models import NotificationEvent, NotificationLog

from tests.helpers import create_account
from tests.sms_outbox import OUTBOX, PUSH_OUTBOX

API = settings.API_V1_PREFIX
NUMBER = "1234567890123"
ANSWER = "12 juin 1995"


def _finder(client):
    return create_account(client, "78 111 22 33", "Moussa Fall")


def _owner(client):
    return create_account(client, "77 123 45 67", "Awa Diop")


def _declare(client, headers, kind="found", number=NUMBER, with_question=False):
    payload = {
        "kind": kind,
        "document_type": "cni",
        "document_number": number,
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
    }
    if with_question:
        payload["verification_question"] = "Date de naissance sur la carte ?"
        payload["verification_answer"] = ANSWER

    return client.post(f"{API}/reports", json=payload, headers=headers).json()


def _events(db):
    return [entry.event for entry in db.scalars(select(NotificationLog))]


# ---------------------------------------------------------------------------
# Correspondance automatique
# ---------------------------------------------------------------------------


def test_matching_report_notifies_both_sides(client, db_session):
    """Le cœur du service : personne n'a besoin d'ouvrir l'application
    pour apprendre que sa pièce a été retrouvée."""
    owner = _owner(client)
    finder = _finder(client)

    _declare(client, owner, kind="lost")
    OUTBOX.clear()
    _declare(client, finder, kind="found")

    events = _events(db_session)
    assert events.count(NotificationEvent.MATCH_FOUND) == 2
    assert len(OUTBOX.messages) == 2


def test_no_notification_without_a_match(client, db_session):
    owner = _owner(client)
    finder = _finder(client)

    _declare(client, owner, kind="lost", number="1111111111111")
    OUTBOX.clear()
    _declare(client, finder, kind="found", number="2222222222222")

    assert _events(db_session) == []
    assert OUTBOX.messages == []


def test_a_match_is_announced_only_once(client, db_session):
    owner = _owner(client)
    finder = _finder(client)

    _declare(client, owner, kind="lost")
    _declare(client, finder, kind="found")
    # Un troisième signalement identique ne renotifie pas la même paire
    _declare(client, finder, kind="found", number="3333333333333")

    assert _events(db_session).count(NotificationEvent.MATCH_FOUND) == 2


def test_push_is_used_when_a_device_is_registered(client, db_session):
    owner = _owner(client)
    finder = _finder(client)
    client.post(
        f"{API}/devices",
        json={"token": "token-appareil-awa", "platform": "android"},
        headers=owner,
    )

    _declare(client, owner, kind="lost")
    PUSH_OUTBOX.clear()
    OUTBOX.clear()
    _declare(client, finder, kind="found")

    # Awa a un appareil, Moussa non
    assert len(PUSH_OUTBOX.messages) == 1
    assert len(OUTBOX.messages) == 1


# ---------------------------------------------------------------------------
# Revendications
# ---------------------------------------------------------------------------


def test_claim_notifies_the_report_owner(client, db_session):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    OUTBOX.clear()

    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    assert NotificationEvent.CLAIM_RECEIVED in _events(db_session)
    assert len(OUTBOX.messages) == 1


def test_approval_notifies_the_claimant(client, db_session):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    claim_id = client.post(
        f"{API}/reports/{report_id}/claims", json={}, headers=owner
    ).json()["id"]
    OUTBOX.clear()

    client.post(f"{API}/claims/{claim_id}/approve", headers=finder)

    assert NotificationEvent.CLAIM_APPROVED in _events(db_session)


def test_rejection_notifies_the_claimant(client, db_session):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    claim_id = client.post(
        f"{API}/reports/{report_id}/claims", json={}, headers=owner
    ).json()["id"]

    client.post(f"{API}/claims/{claim_id}/reject", headers=finder)

    assert NotificationEvent.CLAIM_REJECTED in _events(db_session)


def test_withdrawal_notifies_nobody(client, db_session):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    claim_id = client.post(
        f"{API}/reports/{report_id}/claims", json={}, headers=owner
    ).json()["id"]

    events_before = len(_events(db_session))
    client.post(f"{API}/claims/{claim_id}/withdraw", headers=owner)

    assert len(_events(db_session)) == events_before


# ---------------------------------------------------------------------------
# Appareils
# ---------------------------------------------------------------------------


def test_device_registration_requires_authentication(client):
    response = client.post(
        f"{API}/devices", json={"token": "token-appareil", "platform": "android"}
    )

    assert response.status_code == 401


def test_unknown_platform_is_rejected(client):
    headers = _owner(client)

    response = client.post(
        f"{API}/devices",
        json={"token": "token-appareil", "platform": "windows"},
        headers=headers,
    )

    assert response.status_code == 422


def test_device_can_be_unregistered(client):
    headers = _owner(client)
    client.post(
        f"{API}/devices",
        json={"token": "token-appareil", "platform": "android"},
        headers=headers,
    )

    response = client.request(
        "DELETE", f"{API}/devices", json={"token": "token-appareil"}, headers=headers
    )

    assert response.status_code == 204