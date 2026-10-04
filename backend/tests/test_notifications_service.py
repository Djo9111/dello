import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.notifications import service
from app.modules.notifications.models import (
    DeviceToken,
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from app.modules.users.models import User

from tests.sms_outbox import OUTBOX, PUSH_OUTBOX

EVENT = NotificationEvent.CLAIM_RECEIVED


def _user(db, phone="+221771234567", verified=True) -> User:
    user = User(
        phone_number=phone,
        full_name="Awa Diop",
        hashed_password=hash_password("Tamarin-Soleil-9"),
        is_phone_verified=verified,
    )
    db.add(user)
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Choix du canal
# ---------------------------------------------------------------------------


def test_sms_when_no_device_is_registered(db_session):
    user = _user(db_session)

    entry = service.notify(db_session, user, EVENT)

    assert entry.channel is NotificationChannel.SMS
    assert entry.status is NotificationStatus.SENT
    assert len(OUTBOX.messages) == 1
    assert OUTBOX.messages[0][0] == user.phone_number


def test_push_when_a_device_is_registered(db_session):
    user = _user(db_session)
    service.register_device(db_session, user, "token-appareil-1", "android")

    entry = service.notify(db_session, user, EVENT)

    assert entry.channel is NotificationChannel.PUSH
    assert len(PUSH_OUTBOX.messages) == 1
    assert OUTBOX.messages == []


def test_push_reaches_every_device(db_session):
    user = _user(db_session)
    service.register_device(db_session, user, "token-appareil-1", "android")
    service.register_device(db_session, user, "token-appareil-2", "ios")

    service.notify(db_session, user, EVENT)

    assert len(PUSH_OUTBOX.messages) == 2


def test_sms_messages_stay_in_the_gsm_alphabet(db_session):
    """Un accent fait basculer le SMS en Unicode, donc double le coût."""
    for _, body in service.MESSAGES.values():
        assert body.isascii()


# ---------------------------------------------------------------------------
# Anti-doublon
# ---------------------------------------------------------------------------


def test_same_event_is_sent_once(db_session):
    user = _user(db_session)
    key = f"claim_received:{uuid.uuid4()}"

    first = service.notify(db_session, user, EVENT, dedup_key=key)
    second = service.notify(db_session, user, EVENT, dedup_key=key)

    assert first is not None
    assert second is None
    assert len(OUTBOX.messages) == 1


def test_different_keys_are_both_sent(db_session):
    user = _user(db_session)

    service.notify(db_session, user, EVENT, dedup_key="a")
    service.notify(db_session, user, EVENT, dedup_key="b")

    assert len(db_session.scalars(select(NotificationLog)).all()) == 2


def test_without_key_nothing_is_deduplicated(db_session):
    user = _user(db_session)

    service.notify(db_session, user, EVENT)
    service.notify(db_session, user, EVENT)

    assert len(OUTBOX.messages) == 2


# ---------------------------------------------------------------------------
# Appareils
# ---------------------------------------------------------------------------


def test_registering_twice_updates_the_device(db_session):
    user = _user(db_session)

    service.register_device(db_session, user, "token-appareil-1", "android")
    service.register_device(db_session, user, "token-appareil-1", "android")

    assert len(db_session.scalars(select(DeviceToken)).all()) == 1


def test_a_device_can_change_owner(db_session):
    """Deux personnes peuvent utiliser le même téléphone."""
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")

    service.register_device(db_session, awa, "token-partage", "android")
    service.register_device(db_session, moussa, "token-partage", "android")

    devices = db_session.scalars(select(DeviceToken)).all()
    assert len(devices) == 1
    assert devices[0].user_id == moussa.id


def test_unregistering_falls_back_to_sms(db_session):
    user = _user(db_session)
    service.register_device(db_session, user, "token-appareil-1", "android")

    service.unregister_device(db_session, user, "token-appareil-1")
    entry = service.notify(db_session, user, EVENT)

    assert entry.channel is NotificationChannel.SMS


def test_a_device_of_someone_else_is_not_removed(db_session):
    awa = _user(db_session)
    moussa = _user(db_session, phone="+221781112233")
    service.register_device(db_session, awa, "token-appareil-1", "android")

    service.unregister_device(db_session, moussa, "token-appareil-1")

    assert len(db_session.scalars(select(DeviceToken)).all()) == 1


def test_devices_are_deleted_with_the_account(db_session):
    user = _user(db_session)
    service.register_device(db_session, user, "token-appareil-1", "android")

    db_session.delete(user)
    db_session.commit()

    assert db_session.scalars(select(DeviceToken)).all() == []


def test_log_survives_the_account_deletion(db_session):
    """La trace reste, l'identité disparaît."""
    user = _user(db_session)
    service.notify(db_session, user, EVENT)

    db_session.delete(user)
    db_session.commit()

    entries = db_session.scalars(select(NotificationLog)).all()
    assert len(entries) == 1
    assert entries[0].user_id is None


# ---------------------------------------------------------------------------
# Robustesse
# ---------------------------------------------------------------------------


def test_a_failing_sender_is_logged_not_raised(db_session, monkeypatch):
    user = _user(db_session)

    class BrokenSender:
        def send(self, *args, **kwargs):
            raise RuntimeError("operateur injoignable")

    monkeypatch.setattr(service, "get_sms_sender", lambda: BrokenSender())

    entry = service.notify(db_session, user, EVENT)

    assert entry.status is NotificationStatus.FAILED

def test_unverified_number_without_device_waits_in_the_app(db_session):
    """Plus rien n'est perdu : sans appareil ni numéro vérifié, la
    notification reste consultable dans l'application."""
    user = _user(db_session, verified=False)

    entry = service.notify(db_session, user, EVENT)

    assert entry.channel is NotificationChannel.IN_APP
    assert entry.read_at is None
    assert OUTBOX.messages == []    