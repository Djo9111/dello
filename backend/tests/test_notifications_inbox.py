from sqlalchemy import select

from app.core.config import settings
from app.modules.notifications.models import NotificationChannel, NotificationLog

from tests.helpers import create_account
from tests.sms_outbox import OUTBOX

API = settings.API_V1_PREFIX
NUMBER = "1234567890123"


def _finder(client):
    return create_account(client, "78 111 22 33", "Moussa Fall")


def _owner(client):
    return create_account(client, "77 123 45 67", "Awa Diop")


def _declare(client, headers, kind="found", number=NUMBER):
    payload = {
        "kind": kind,
        "documents": [{"document_type": "cni", "document_number": number}],
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
    }
    return client.post(f"{API}/reports", json=payload, headers=headers).json()


def _inbox(client, headers):
    return client.get(f"{API}/notifications", headers=headers).json()


def _unread(client, headers):
    return client.get(f"{API}/notifications/unread-count", headers=headers).json()["unread"]


# ---------------------------------------------------------------------------
# Réception
# ---------------------------------------------------------------------------


def test_a_claim_appears_in_the_owner_inbox(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]

    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    inbox = _inbox(client, finder)
    assert len(inbox) == 1
    assert inbox[0]["event"] == "claim_received"
    assert inbox[0]["title"]
    assert inbox[0]["is_read"] is False


def test_a_match_reaches_both_inboxes(client):
    owner = _owner(client)
    finder = _finder(client)

    _declare(client, owner, kind="lost")
    _declare(client, finder, kind="found")

    assert _unread(client, owner) == 1
    assert _unread(client, finder) == 1


def test_the_inbox_is_personal(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    assert _inbox(client, owner) == []


def test_target_allows_navigation(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    claim_id = client.post(
        f"{API}/reports/{report_id}/claims", json={}, headers=owner
    ).json()["id"]

    assert _inbox(client, finder)[0]["target_id"] == claim_id


def test_notification_is_kept_even_without_external_channel(
    no_verification_client, db_session
):
    """Sans appareil inscrit ni numéro vérifié, la notification attend
    dans l'application au lieu d'être perdue. C'est le cas de tous les
    comptes tant qu'aucun fournisseur de SMS n'est branché."""
    client = no_verification_client
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    OUTBOX.clear()

    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    entry = db_session.scalar(select(NotificationLog))
    assert entry.channel is NotificationChannel.IN_APP
    assert OUTBOX.messages == []


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def test_marking_one_as_read(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    notification_id = _inbox(client, finder)[0]["id"]
    response = client.post(f"{API}/notifications/{notification_id}/read", headers=finder)

    assert response.status_code == 204
    assert _unread(client, finder) == 0
    assert _inbox(client, finder)[0]["is_read"] is True


def test_marking_all_as_read(client):
    owner = _owner(client)
    finder = _finder(client)
    _declare(client, owner, kind="lost")
    _declare(client, finder, kind="found")

    client.post(f"{API}/notifications/read-all", headers=owner)

    assert _unread(client, owner) == 0


def test_cannot_mark_someone_else_notification(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _declare(client, finder)["id"]
    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)
    notification_id = _inbox(client, finder)[0]["id"]

    response = client.post(f"{API}/notifications/{notification_id}/read", headers=owner)

    assert response.status_code == 404
    assert _unread(client, finder) == 1


def test_unknown_notification(client):
    headers = _owner(client)

    response = client.post(
        f"{API}/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=headers,
    )

    assert response.status_code == 404


def test_inbox_requires_authentication(client):
    assert client.get(f"{API}/notifications").status_code == 401
    assert client.get(f"{API}/notifications/unread-count").status_code == 401