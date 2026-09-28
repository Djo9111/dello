import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"      # en attente de la décision du déclarant
    VERIFIED = "verified"    # mise en relation active, contacts échangés
    REJECTED = "rejected"    # refusée par le déclarant
    WITHDRAWN = "withdrawn"  # annulée par le demandeur


class Claim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Demande de mise en relation sur un signalement."""

    __tablename__ = "claims"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    claimant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[ClaimStatus] = mapped_column(
        Enum(
            ClaimStatus,
            name="claim_status",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=ClaimStatus.PENDING,
        server_default=ClaimStatus.PENDING.value,
    )

    message: Mapped[str | None] = mapped_column(String(300))

    # Nombre de réponses fausses à la question de vérification.
    # Au-delà de la limite, la demande passe en validation manuelle.
    answer_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report = relationship("Report")
    claimant = relationship("User")

    __table_args__ = (
        # Une seule demande par personne et par signalement
        UniqueConstraint("report_id", "claimant_id", name="one_claim_per_person"),
    )

    def __repr__(self) -> str:
        return f"<Claim id={self.id} status={self.status}>"