from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import decode_access_token, hash_refresh_token
from app.modules.auth import service
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PhoneAlreadyRegisteredError,
)
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.users.models import User

PHONE = "+221771234567"
PASSWORD = "Tamarin-Soleil-9"


def _register(db, phone=PHONE, password=PASSWORD) -> User:
    return service.register(
        db,
        RegisterRequest(phone_number=phone, full_name="Awa Diop", password=password),
    )


def _login(db, phone=PHONE, password=PASSWORD):
    return service.login(db, LoginRequest(phone_number=phone, password=password))


# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------


def test_register_stores_hashed_password(db_session):
    user = _register(db_session)

    assert user.phone_number == PHONE
    assert user.hashed_password.startswith("$argon2")
    assert PASSWORD not in user.hashed_password


def test_register_duplicate_phone_is_rejected(db_session):
    _register(db_session)

    with pytest.raises(PhoneAlreadyRegisteredError):
        _register(db_session, phone="77 123 45 67")


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------


def test_login_returns_valid_tokens(db_session):
    user = _register(db_session)

    tokens = _login(db_session)

    assert decode_access_token(tokens.access_token) == user.id
    assert tokens.expires_in > 0


def test_refresh_token_is_stored_hashed(db_session):
    _register(db_session)
    tokens = _login(db_session)

    stored = db_session.scalars(select(RefreshToken.token_hash)).all()

    assert tokens.refresh_token not in stored
    assert hash_refresh_token(tokens.refresh_token) in stored


def test_login_sets_last_login(db_session):
    user = _register(db_session)
    _login(db_session)

    db_session.refresh(user)
    assert user.last_login_at is not None


def test_unknown_phone_is_rejected(db_session):
    with pytest.raises(InvalidCredentialsError):
        _login(db_session)


def test_wrong_password_increments_counter(db_session):
    user = _register(db_session)

    with pytest.raises(InvalidCredentialsError):
        _login(db_session, password="mauvais-mot-de-passe")

    db_session.refresh(user)
    assert user.failed_login_count == 1


def test_account_locks_after_max_failures(db_session):
    user = _register(db_session)

    for _ in range(service.MAX_FAILED_LOGIN_ATTEMPTS):
        with pytest.raises(InvalidCredentialsError):
            _login(db_session, password="mauvais-mot-de-passe")

    # Même le bon mot de passe est refusé pendant le verrouillage
    with pytest.raises(InvalidCredentialsError):
        _login(db_session)

    db_session.refresh(user)
    assert user.locked_until is not None


def test_lock_expires(db_session):
    user = _register(db_session)
    user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    _login(db_session)

    db_session.refresh(user)
    assert user.locked_until is None


def test_success_resets_counter(db_session):
    user = _register(db_session)

    with pytest.raises(InvalidCredentialsError):
        _login(db_session, password="mauvais-mot-de-passe")
    _login(db_session)

    db_session.refresh(user)
    assert user.failed_login_count == 0


def test_inactive_user_cannot_login(db_session):
    user = _register(db_session)
    user.is_active = False
    db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        _login(db_session)


# ---------------------------------------------------------------------------
# Rafraîchissement
# ---------------------------------------------------------------------------


def test_refresh_rotates_tokens(db_session):
    _register(db_session)
    first = _login(db_session)

    second = service.refresh_tokens(db_session, first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert second.access_token != first.access_token


def test_reused_refresh_token_revokes_whole_family(db_session):
    _register(db_session)
    first = _login(db_session)
    second = service.refresh_tokens(db_session, first.refresh_token)

    # L'ancien token revient : vol détecté
    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, first.refresh_token)

    # Le token légitime le plus récent est aussi révoqué
    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, second.refresh_token)


def test_reuse_does_not_affect_other_devices(db_session):
    _register(db_session)
    phone_a = _login(db_session)
    phone_b = _login(db_session)

    service.refresh_tokens(db_session, phone_a.refresh_token)
    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, phone_a.refresh_token)

    # L'autre appareil (autre famille) continue de fonctionner
    service.refresh_tokens(db_session, phone_b.refresh_token)


def test_expired_refresh_token_is_rejected(db_session):
    _register(db_session)
    tokens = _login(db_session)

    stored = db_session.scalar(select(RefreshToken))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, tokens.refresh_token)


def test_unknown_refresh_token_is_rejected(db_session):
    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, "x" * 64)


def test_inactive_user_cannot_refresh(db_session):
    user = _register(db_session)
    tokens = _login(db_session)

    user.is_active = False
    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, tokens.refresh_token)


# ---------------------------------------------------------------------------
# Déconnexion
# ---------------------------------------------------------------------------


def test_logout_revokes_refresh_token(db_session):
    _register(db_session)
    tokens = _login(db_session)

    service.logout(db_session, tokens.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh_tokens(db_session, tokens.refresh_token)


def test_logout_with_unknown_token_is_silent(db_session):
    service.logout(db_session, "x" * 64)


def test_logout_all_only_affects_that_user(db_session):
    awa = _register(db_session)
    awa_phone_1 = _login(db_session)
    awa_phone_2 = _login(db_session)

    _register(db_session, phone="+221781112233")
    moussa = _login(db_session, phone="+221781112233")

    service.logout_all(db_session, awa.id)

    for tokens in (awa_phone_1, awa_phone_2):
        with pytest.raises(InvalidRefreshTokenError):
            service.refresh_tokens(db_session, tokens.refresh_token)

    service.refresh_tokens(db_session, moussa.refresh_token)