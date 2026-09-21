import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings

# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

_password_hash = PasswordHash((Argon2Hasher(),))
_DUMMY_HASH = _password_hash.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Mot de passe trop long")
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> tuple[bool, str | None]:
    """
    Retourne (valide, nouveau_hash).
    nouveau_hash est renseigné si les paramètres Argon2 ont évolué :
    il faut alors le sauvegarder à la place de l'ancien.
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        fake_password_verification()
        return False, None
    return _password_hash.verify_and_update(password, hashed_password)


def fake_password_verification() -> None:
    """
    À appeler quand le compte n'existe pas, pour que la réponse prenne
    le même temps qu'une vraie vérification (anti énumération des comptes).
    """
    _password_hash.verify("dello-dummy-password", _DUMMY_HASH)


# ---------------------------------------------------------------------------
# Access token (JWT)
# ---------------------------------------------------------------------------

JWT_ISSUER = "dello-api"
JWT_AUDIENCE = "dello-mobile"
ACCESS_TOKEN_TYPE = "access"


class TokenError(Exception):
    """Token invalide, expiré, falsifié ou mal formé."""


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> uuid.UUID:
    """Retourne l'id utilisateur, ou lève TokenError."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["sub", "type", "iss", "aud", "iat", "exp", "jti"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token invalide") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("Type de token invalide")

    try:
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise TokenError("Token invalide") from exc


# ---------------------------------------------------------------------------
# Refresh token (opaque, stocké haché)
# ---------------------------------------------------------------------------

REFRESH_TOKEN_BYTES = 48


def generate_refresh_token() -> tuple[str, str]:
    """
    Retourne (token_brut, token_haché).
    Le brut est envoyé une seule fois au mobile, seul le haché est stocké.
    """
    raw_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    return raw_token, hash_refresh_token(raw_token)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Numéros de documents (HMAC)
# ---------------------------------------------------------------------------


def normalize_document_number(number: str) -> str:
    """Majuscules, lettres et chiffres ASCII uniquement."""
    return "".join(ch for ch in number.upper() if ch.isascii() and ch.isalnum())


def hash_document_number(document_type: str, number: str) -> str:
    normalized = normalize_document_number(number)
    if not normalized:
        raise ValueError("Numéro de document vide")

    message = f"{document_type.lower()}:{normalized}".encode("utf-8")
    key = settings.DOCUMENT_HMAC_KEY.get_secret_value().encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()