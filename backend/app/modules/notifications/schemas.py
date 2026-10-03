from typing import Literal

from pydantic import Field, field_validator

from app.shared.schemas import StrictModel


class DeviceRegisterRequest(StrictModel):
    token: str = Field(min_length=10, max_length=255)
    platform: Literal["android", "ios"]

    @field_validator("token")
    @classmethod
    def clean_token(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Jeton invalide")
        return cleaned


class DeviceUnregisterRequest(StrictModel):
    token: str = Field(min_length=10, max_length=255)