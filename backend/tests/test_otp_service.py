from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.otp import service
from app.modules.otp.exceptions import InvalidOtpError, OtpThrottledError
from app.modules.otp.models import OtpCode, OtpPurpose, PendingRegistration

PHONE = "+221771234567"
PURPOSE = OtpPurpose.PHONE_VERIFICATION


def _age_last_code(db, seconds: int) -> OtpCode:
    """Vieillit le dernier code pour contourner le délai entre deux envois."""
    otp = db.scalars(select(OtpCode).order_by(OtpCode.created_at.desc())).first()
    otp.created_at = datetime.now(UTC) - timedelta(seconds=seconds)
    db.commit()
    return otp


# ---------------------------------------------------------------------------
# Génération
# ---------------------------------------------------------------------------


def test_code_is_six_digits():
    for _ in range(50):
        code = service.generate_code()
        assert len(code) == 6
        assert code.isdigit()


def test_codes_are_not_repetitive():
    codes = {service.generate_code() for _ in range(200)}

    assert len(codes) > 150


def test_code_is_never_stored_in_clear(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)

    stored = db_session.scalar(select(OtpCode))
    assert code not in stored.code_hash
    assert stored.code_hash.startswith("$argon2")


# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------


def test_right_code_passes(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)

    service.verify_code(db_session, PHONE, code, PURPOSE)

    stored = db_session.scalar(select(OtpCode))
    assert stored.consumed_at is not None


def test_code_cannot_be_used_twice(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)
    service.verify_code(db_session, PHONE, code, PURPOSE)

    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, code, PURPOSE)


def test_wrong_code_is_rejected_and_counted(db_session):
    service.issue_code(db_session, PHONE, PURPOSE)

    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, "000000", PURPOSE)

    assert db_session.scalar(select(OtpCode)).attempts == 1


def test_attempts_are_limited(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)

    for _ in range(settings.OTP_MAX_ATTEMPTS):
        with pytest.raises(InvalidOtpError):
            service.verify_code(db_session, PHONE, "000000", PURPOSE)

    # Même le bon code ne passe plus
    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, code, PURPOSE)


def test_expired_code_is_rejected(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)
    otp = db_session.scalar(select(OtpCode))
    otp.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, code, PURPOSE)


def test_code_of_another_number_is_rejected(db_session):
    code = service.issue_code(db_session, PHONE, PURPOSE)

    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, "+221781112233", code, PURPOSE)


def test_verifying_without_any_code_is_rejected(db_session):
    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, "123456", PURPOSE)


def test_new_code_invalidates_the_previous_one(db_session):
    first = service.issue_code(db_session, PHONE, PURPOSE)
    _age_last_code(db_session, settings.OTP_RESEND_COOLDOWN_SECONDS + 5)
    second = service.issue_code(db_session, PHONE, PURPOSE)

    with pytest.raises(InvalidOtpError):
        service.verify_code(db_session, PHONE, first, PURPOSE)

    service.verify_code(db_session, PHONE, second, PURPOSE)


# ---------------------------------------------------------------------------
# Limitation des envois
# ---------------------------------------------------------------------------


def test_resend_is_throttled(db_session):
    service.issue_code(db_session, PHONE, PURPOSE)

    with pytest.raises(OtpThrottledError) as exc_info:
        service.check_can_send(db_session, PHONE, PURPOSE)

    assert exc_info.value.retry_after_seconds > 0


def test_resend_allowed_after_cooldown(db_session):
    service.issue_code(db_session, PHONE, PURPOSE)
    _age_last_code(db_session, settings.OTP_RESEND_COOLDOWN_SECONDS + 5)

    service.check_can_send(db_session, PHONE, PURPOSE)


def test_hourly_limit(db_session):
    for _ in range(settings.OTP_MAX_PER_HOUR):
        service.issue_code(db_session, PHONE, PURPOSE)
        _age_last_code(db_session, settings.OTP_RESEND_COOLDOWN_SECONDS + 5)

    with pytest.raises(OtpThrottledError):
        service.check_can_send(db_session, PHONE, PURPOSE)


def test_limits_are_per_number(db_session):
    service.issue_code(db_session, PHONE, PURPOSE)

    service.check_can_send(db_session, "+221781112233", PURPOSE)


# ---------------------------------------------------------------------------
# Inscriptions en attente
# ---------------------------------------------------------------------------


def test_pending_registration_stores_hashed_password(db_session):
    service.save_pending_registration(db_session, PHONE, "Awa Diop", "Tamarin-Soleil-9")

    pending = db_session.scalar(select(PendingRegistration))
    assert pending.hashed_password.startswith("$argon2")
    assert "Tamarin-Soleil-9" not in pending.hashed_password


def test_new_registration_replaces_the_previous_one(db_session):
    service.save_pending_registration(db_session, PHONE, "Awa Diop", "Tamarin-Soleil-9")
    service.save_pending_registration(db_session, PHONE, "Awa Ndiaye", "Tamarin-Soleil-9")

    pendings = db_session.scalars(select(PendingRegistration)).all()
    assert len(pendings) == 1
    assert pendings[0].full_name == "Awa Ndiaye"


def test_expired_registration_is_not_returned(db_session):
    pending = service.save_pending_registration(
        db_session, PHONE, "Awa Diop", "Tamarin-Soleil-9"
    )
    pending.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    assert service.get_pending_registration(db_session, PHONE) is None


def test_purge_removes_expired_rows(db_session):
    pending = service.save_pending_registration(
        db_session, PHONE, "Awa Diop", "Tamarin-Soleil-9"
    )
    pending.expires_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    assert service.purge_expired(db_session) >= 1
    assert db_session.scalars(select(PendingRegistration)).all() == []