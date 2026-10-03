import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationEvent(str, enum.Enum):
    CLAIM_RECEIVED = "claim_received"
    CLAIM_APPROVED = "claim_approved"
    CLAIM_REJECTED = "claim_rejected"
    MATCH_FOUND = "match_found"


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"


def _pg_enum(enum_class, name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=30,
        values_callable=lambda members: [member.value for member in members],
    )


class DeviceToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Appareil inscrit aux notifications push."""

    __tablename__ = "device_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True)
    platform: Mapped[str] = mapped_column(String(20))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<DeviceToken id={self.id}>"


class NotificationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Trace des envois.

    Sert à ne pas prévenir deux fois pour la même chose, ce qui compte
    d'autant plus que chaque SMS est payant. Le lien vers l'utilisateur
    passe à NULL si le compte est supprimé : la trace reste, l'identité
    disparaît.
    """

    __tablename__ = "notification_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    event: Mapped[NotificationEvent] = mapped_column(
        _pg_enum(NotificationEvent, "notification_event")
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _pg_enum(NotificationChannel, "notification_channel")
    )
    status: Mapped[NotificationStatus] = mapped_column(
        _pg_enum(NotificationStatus, "notification_status")
    )

    # Identifie l'objet concerné sans contrainte de clé étrangère :
    # il peut s'agir d'une demande comme d'un signalement.
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Empreinte de l'événement, pour ne pas renvoyer le même message
    dedup_key: Mapped[str | None] = mapped_column(String(120))

    __table_args__ = (
        UniqueConstraint("dedup_key", name="one_message_per_event"),
    )

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.id} event={self.event}>"