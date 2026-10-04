import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)
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


class NotificationRead(BaseModel):
    """Une notification telle qu'affichée dans l'application.

    Le titre et le texte ne sont pas stockés : ils sont reconstruits à
    partir de l'événement, ce qui permet de les corriger ou de les
    traduire sans toucher aux données déjà enregistrées.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: NotificationEvent
    title: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus
    target_id: uuid.UUID | None
    is_read: bool
    created_at: datetime

    @classmethod
    def from_entry(cls, entry, title: str, body: str) -> "NotificationRead":
        return cls(
            id=entry.id,
            event=entry.event,
            title=title,
            body=body,
            channel=entry.channel,
            status=entry.status,
            target_id=entry.target_id,
            is_read=entry.read_at is not None,
            created_at=entry.created_at,
        )


class UnreadCount(BaseModel):
    unread: int