import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, SecretStr

from app.shared.schemas import StrictModel


class UserRead(BaseModel):
    """Ce que l'API renvoie sur un utilisateur. Liste blanche : rien d'autre ne sort."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    full_name: str
    is_phone_verified: bool
    created_at: datetime


class DeleteAccountRequest(StrictModel):
    """Confirmation par mot de passe avant suppression définitive."""

    password: SecretStr