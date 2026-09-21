import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.config import settings

# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------


def test_hash_password_is_argon2_and_salted():
    first = security.hash_password("MotDePasse-Solide-42")
    second = security.hash_password("MotDePasse-Solide-42")

    assert first.startswith("$argon2")
    assert first != second


def test_verify_password_accepts_right_and_rejects_wrong():
    hashed = security.hash_password("MotDePasse-Solide-42")

    valid, _ = security.verify_password("MotDePasse-Solide-42", hashed)
    invalid, _ = security.verify_password("mauvais-mot-de-passe", hashed)

    assert valid is True
    assert invalid is False


def test_too_long_password_is_rejected():
    too_long = "a" * (security.MAX_PASSWORD_LENGTH + 1)

    with pytest.raises(ValueError):
        security.hash_password(too_long)

    hashed = security.hash_password("MotDePasse-Solide-42")
    valid, _ = security.verify_password(too_long, hashed)
    assert valid is False


def test_fake_password_verification_runs():
    security.fake_password_verification()


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


def _payload(**overrides):
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "type": security.ACCESS_TOKEN_TYPE,
        "iss": security.JWT_ISSUER,
        "aud": security.JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


def _sign(payload, key=None):
    return jwt.encode(
        payload,
        key or settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id)

    assert security.decode_access_token(token) == user_id


def test_access_token_contains_no_personal_data():
    token = security.create_access_token(uuid.uuid4())
    claims = jwt.decode(token, options={"verify_signature": False})

    assert set(claims) == {"sub", "type", "iss", "aud", "iat", "exp", "jti"}


def test_expired_token_is_rejected():
    token = _sign(_payload(exp=datetime.now(UTC) - timedelta(minutes=1)))

    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_token_signed_with_other_key_is_rejected():
    token = _sign(_payload(), key="cle-pirate-" * 8)

    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_forged_payload_is_rejected():
    token_a = security.create_access_token(uuid.uuid4())
    token_b = security.create_access_token(uuid.uuid4())

    header_a, _, signature_a = token_a.split(".")
    _, payload_b, _ = token_b.split(".")
    forged = f"{header_a}.{payload_b}.{signature_a}"

    with pytest.raises(security.TokenError):
        security.decode_access_token(forged)


def test_wrong_token_type_is_rejected():
    token = _sign(_payload(type="refresh"))

    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_wrong_audience_is_rejected():
    token = _sign(_payload(aud="autre-app"))

    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_missing_claim_is_rejected():
    payload = _payload()
    del payload["jti"]

    with pytest.raises(security.TokenError):
        security.decode_access_token(_sign(payload))


def test_garbage_token_is_rejected():
    with pytest.raises(security.TokenError):
        security.decode_access_token("pas.un.token")


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------


def test_refresh_token_generation():
    raw, hashed = security.generate_refresh_token()

    assert len(raw) >= 64
    assert raw != hashed
    assert security.hash_refresh_token(raw) == hashed


def test_refresh_tokens_are_unique():
    tokens = {security.generate_refresh_token()[0] for _ in range(100)}

    assert len(tokens) == 100


# ---------------------------------------------------------------------------
# Numéros de documents
# ---------------------------------------------------------------------------


def test_document_hash_ignores_formatting():
    formatted = security.hash_document_number("cni", "1 234-567.89")
    raw = security.hash_document_number("CNI", "123456789")

    assert formatted == raw


def test_document_hash_depends_on_type():
    assert security.hash_document_number(
        "cni", "123456789"
    ) != security.hash_document_number("permis", "123456789")


def test_document_hash_is_not_plain_sha256():
    keyed = security.hash_document_number("cni", "123456789")
    plain = hashlib.sha256(b"cni:123456789").hexdigest()

    assert keyed != plain


def test_empty_document_number_is_rejected():
    with pytest.raises(ValueError):
        security.hash_document_number("cni", " - . ")