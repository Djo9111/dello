import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.modules.claims.models import ClaimStatus
from app.modules.reports.schemas import ReportPublic
from app.shared.schemas import StrictModel

MAX_ANSWER_LENGTH = 100


class ClaimCreate(StrictModel):
    message: str | None = Field(default=None, max_length=300)

    # Réponse à la question de vérification du signalement, si elle existe.
    # SecretStr : ne doit apparaître ni dans un log ni dans une trace d'erreur.
    answer: SecretStr | None = None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("answer")
    @classmethod
    def check_answer_length(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value().strip()
        if not raw:
            return None
        if len(raw) > MAX_ANSWER_LENGTH:
            raise ValueError(f"Réponse trop longue ({MAX_ANSWER_LENGTH} caractères max)")
        return value


class ClaimAnswer(StrictModel):
    answer: SecretStr

    @field_validator("answer")
    @classmethod
    def check_answer(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("Réponse vide")
        if len(raw) > MAX_ANSWER_LENGTH:
            raise ValueError(f"Réponse trop longue ({MAX_ANSWER_LENGTH} caractères max)")
        return value


class ClaimRead(BaseModel):
    """Vue d'une demande. Ne contient jamais de coordonnées :
    le contact s'obtient par une route séparée, et seulement si la
    demande est acceptée."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ClaimStatus
    message: str | None
    answer_attempts: int
    created_at: datetime
    resolved_at: datetime | None
    report: ReportPublic


class ContactRead(BaseModel):
    """Coordonnées de l'autre partie, une fois la demande acceptée."""

    model_config = ConfigDict(from_attributes=True)

    full_name: str
    phone_number: str