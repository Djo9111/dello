import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest

VALID_PASSWORD = "Tamarin-Soleil-9"


def _register(**overrides):
    data = {
        "phone_number": "77 123 45 67",
        "full_name": "Awa Diop",
        "password": VALID_PASSWORD,
    }
    data.update(overrides)
    return RegisterRequest(**data)


def test_valid_registration_is_normalized():
    request = _register()

    assert request.phone_number == "+221771234567"
    assert request.password.get_secret_value() == VALID_PASSWORD


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        _register(role="admin")

    with pytest.raises(ValidationError):
        _register(is_phone_verified=True)


@pytest.mark.parametrize(
    "password",
    [
        "court",  # trop court
        "a" * 129,  # trop long
        "azertyuiop",  # trop courant
        "AZERTYUIOP",  # courant, casse différente
        "xx771234567",  # contient le numéro
        "abababababab",  # trop répétitif
    ],
)
def test_weak_passwords_are_rejected(password):
    with pytest.raises(ValidationError):
        _register(password=password)


def test_password_is_not_in_error_text():
    secret = "azertyuiop"

    with pytest.raises(ValidationError) as exc_info:
        _register(password=secret)

    assert secret not in str(exc_info.value)


def test_password_is_masked_in_repr():
    request = _register()

    assert VALID_PASSWORD not in repr(request)


def test_login_does_not_enforce_registration_rules():
    request = LoginRequest(phone_number="+221771234567", password="x")

    assert request.phone_number == "+221771234567"


def test_login_rejects_huge_password():
    with pytest.raises(ValidationError):
        LoginRequest(phone_number="771234567", password="a" * 129)


@pytest.mark.parametrize("token", ["court", "a" * 129])
def test_refresh_token_length_is_checked(token):
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token=token)