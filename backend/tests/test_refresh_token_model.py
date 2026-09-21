import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import generate_refresh_token, hash_password
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User


def _create_user(session, phone: str = "+221770000001") -> User:
    user = User(
        phone_number=phone,
        full_name="Utilisateur Test",
        hashed_password=hash_password("MotDePasse-Solide-42"),
    )
    session.add(user)
    session.commit()
    return user


def _create_token(session, user: User, token_hash: str | None = None) -> RefreshToken:
    if token_hash is None:
        _, token_hash = generate_refresh_token()

    token = RefreshToken(
        user_id=user.id,
        family_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=14),
    )
    session.add(token)
    session.commit()
    return token


def test_tokens_are_deleted_with_user(db_session):
    user = _create_user(db_session)
    _create_token(db_session, user)
    _create_token(db_session, user)

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.scalars(select(RefreshToken)).all()
    assert remaining == []


def test_token_hash_is_unique(db_session):
    user = _create_user(db_session)
    token = _create_token(db_session, user)

    duplicate = RefreshToken(
        user_id=user.id,
        family_id=uuid.uuid4(),
        token_hash=token.token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=14),
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_is_usable():
    now = datetime.now(UTC)

    active = RefreshToken(expires_at=now + timedelta(days=1))
    expired = RefreshToken(expires_at=now - timedelta(seconds=1))
    revoked = RefreshToken(expires_at=now + timedelta(days=1), revoked_at=now)

    assert active.is_usable(now) is True
    assert expired.is_usable(now) is False
    assert revoked.is_usable(now) is False