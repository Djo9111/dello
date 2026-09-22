import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    fake_password_verification,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PhoneAlreadyRegisteredError,
)
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.users.models import User

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------


def register(db: Session, data: RegisterRequest) -> User:
    already_exists = db.scalar(
        select(User.id).where(User.phone_number == data.phone_number)
    )
    if already_exists is not None:
        raise PhoneAlreadyRegisteredError()

    user = User(
        phone_number=data.phone_number,
        full_name=data.full_name,
        hashed_password=hash_password(data.password.get_secret_value()),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        # Deux inscriptions simultanées avec le même numéro
        db.rollback()
        raise PhoneAlreadyRegisteredError() from exc

    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------


def authenticate(db: Session, data: LoginRequest) -> User:
    now = _now()

    # FOR UPDATE : verrouille la ligne pendant la vérification, pour que deux
    # tentatives simultanées ne faussent pas le compteur d'échecs
    user = db.scalar(
        select(User).where(User.phone_number == data.phone_number).with_for_update()
    )

    if user is None:
        fake_password_verification()
        db.rollback()
        raise InvalidCredentialsError()

    if user.locked_until is not None and user.locked_until > now:
        fake_password_verification()
        db.rollback()
        raise InvalidCredentialsError()

    is_valid, new_hash = verify_password(
        data.password.get_secret_value(), user.hashed_password
    )

    if not is_valid:
        _register_failed_attempt(user, now)
        db.commit()
        raise InvalidCredentialsError()

    if not user.is_active:
        db.rollback()
        raise InvalidCredentialsError()

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if new_hash is not None:
        user.hashed_password = new_hash

    db.commit()
    return user


def _register_failed_attempt(user: User, now: datetime) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = now + LOCKOUT_DURATION
        user.failed_login_count = 0


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = authenticate(db, data)
    tokens = _issue_tokens(db, user.id, family_id=uuid.uuid4())
    db.commit()
    return tokens


# ---------------------------------------------------------------------------
# Rafraîchissement (rotation + détection de réutilisation)
# ---------------------------------------------------------------------------


def refresh_tokens(db: Session, raw_refresh_token: str) -> TokenResponse:
    now = _now()

    token = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
        .with_for_update()
    )

    if token is None:
        db.rollback()
        raise InvalidRefreshTokenError()

    if token.revoked_at is not None:
        # Token déjà utilisé qui revient : vol probable, on coupe toute la famille
        _revoke_family(db, token.family_id, now)
        db.commit()
        raise InvalidRefreshTokenError()

    if token.expires_at <= now:
        db.rollback()
        raise InvalidRefreshTokenError()

    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        _revoke_family(db, token.family_id, now)
        db.commit()
        raise InvalidRefreshTokenError()

    token.revoked_at = now
    tokens = _issue_tokens(db, user.id, family_id=token.family_id)
    db.commit()
    return tokens


# ---------------------------------------------------------------------------
# Déconnexion
# ---------------------------------------------------------------------------


def logout(db: Session, raw_refresh_token: str) -> None:
    """Déconnecte l'appareil. Silencieux si le token est inconnu."""
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_refresh_token)
        )
    )
    if token is None:
        return

    _revoke_family(db, token.family_id, _now())
    db.commit()


def logout_all(db: Session, user_id: uuid.UUID) -> None:
    """Déconnecte tous les appareils de l'utilisateur."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()


# ---------------------------------------------------------------------------
# Interne
# ---------------------------------------------------------------------------


def _issue_tokens(db: Session, user_id: uuid.UUID, family_id: uuid.UUID) -> TokenResponse:
    """Crée un couple access/refresh. Le commit est fait par l'appelant."""
    raw_refresh, refresh_hash = generate_refresh_token()

    db.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id,
            token_hash=refresh_hash,
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _revoke_family(db: Session, family_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )