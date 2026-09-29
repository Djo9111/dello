import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OtpPurpose(str, enum.Enum):
    PHONE_VERIFICATION = "phone_verification"
    PASSWORD_RESET = "password_reset"


class OtpCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Code à usage unique envoyé par SMS.

    Le code n'est jamais stocké en clair : six chiffres se retrouveraient
    en une seconde à partir d'un hachage rapide.
    """

    __tablename__ = "otp_codes"

    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    purpose: Mapped[OtpPurpose] = mapped_column(
        Enum(
            OtpPurpose,
            name="otp_purpose",
            native_enum=False,
            create_constraint=True,
            length=30,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    code_hash: Mapped[str] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_otp_codes_lookup", "phone_number", "purpose", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<OtpCode id={self.id} purpose={self.purpose}>"


class PendingRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Inscription en attente de vérification du numéro.

    Le compte n'est créé qu'une fois le code validé : sinon n'importe qui
    pourrait réserver le numéro d'un autre avec un compte jamais vérifié.
    """

    __tablename__ = "pending_registrations"

    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<PendingRegistration id={self.id}>"