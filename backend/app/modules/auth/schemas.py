from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from app.core.security import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.shared.schemas import StrictModel
from app.shared.validators import normalize_full_name, normalize_senegal_mobile

COMMON_PASSWORDS = frozenset(
    {
        "0123456789",
        "1234567890",
        "12345678910",
        "123456789a",
        "azertyuiop",
        "azerty1234",
        "azerty12345",
        "qwertyuiop",
        "password123",
        "password1234",
        "motdepasse",
        "motdepasse1",
        "motdepasse123",
        "senegal2024",
        "senegal2025",
        "senegal2026",
        "senegal123",
        "dakar12345",
        "bonjour123",
        "dello12345",
    }
)


class RegisterRequest(StrictModel):
    phone_number: str = Field(max_length=30)
    full_name: str = Field(max_length=150)
    password: SecretStr

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_senegal_mobile(value)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return normalize_full_name(value)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        length = len(value.get_secret_value())
        if length < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères"
            )
        if length > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Le mot de passe ne doit pas dépasser {MAX_PASSWORD_LENGTH} caractères"
            )
        return value

    @model_validator(mode="after")
    def validate_password_strength(self) -> "RegisterRequest":
        password = self.password.get_secret_value().lower()
        local_number = self.phone_number[-9:]

        if password in COMMON_PASSWORDS:
            raise ValueError("Ce mot de passe est trop courant")
        if local_number in password:
            raise ValueError("Le mot de passe ne doit pas contenir votre numéro")
        if len(set(password)) < 4:
            raise ValueError("Le mot de passe est trop répétitif")

        return self


class LoginRequest(StrictModel):
    phone_number: str = Field(max_length=30)
    password: SecretStr

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return normalize_senegal_mobile(value)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) > MAX_PASSWORD_LENGTH:
            raise ValueError("Identifiants invalides")
        return value


class RefreshRequest(StrictModel):
    refresh_token: SecretStr

    @field_validator("refresh_token")
    @classmethod
    def validate_token_length(cls, value: SecretStr) -> SecretStr:
        if not 32 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Token invalide")
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int