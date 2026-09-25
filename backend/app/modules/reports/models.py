import enum
import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReportKind(str, enum.Enum):
    LOST = "lost"
    FOUND = "found"


class DocumentType(str, enum.Enum):
    CNI = "cni"
    PERMIS = "permis"
    PASSEPORT = "passeport"
    CARTE_ETUDIANT = "carte_etudiant"
    CARTE_CONSULAIRE = "carte_consulaire"
    AUTRE = "autre"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    CLOSED = "closed"


def _pg_enum(enum_class, name: str) -> Enum:
    """Varchar plus contrainte CHECK : meme garantie qu'un ENUM natif,
    sans la difficulte de le faire evoluer en migration."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=30,
        values_callable=lambda members: [member.value for member in members],
    )


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    # ON DELETE SET NULL : un document trouve survit a la suppression
    # du compte de celui qui l'a signale (voir users.service.delete_account)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    kind: Mapped[ReportKind] = mapped_column(_pg_enum(ReportKind, "report_kind"))
    document_type: Mapped[DocumentType] = mapped_column(
        _pg_enum(DocumentType, "document_type")
    )

    # Empreinte HMAC du numero, jamais le numero lui-meme.
    # Nullable : une piece trouvee peut etre illisible ou non saisie.
    document_number_hmac: Mapped[str | None] = mapped_column(String(64))

    # Nom figé masque des la creation (Mod... G...), jamais recalcule a l'affichage
    owner_name_masked: Mapped[str | None] = mapped_column(String(100))

    region: Mapped[str] = mapped_column(String(60))
    commune: Mapped[str | None] = mapped_column(String(80))
    place_detail: Mapped[str | None] = mapped_column(String(255))

    # Date de la perte ou de la trouvaille, distincte de created_at
    occurred_on: Mapped[date | None] = mapped_column(Date)

    status: Mapped[ReportStatus] = mapped_column(
        _pg_enum(ReportStatus, "report_status"),
        default=ReportStatus.OPEN,
        server_default=ReportStatus.OPEN.value,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )

    images: Mapped[list["ReportImage"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "document_number_hmac IS NULL OR char_length(document_number_hmac) = 64",
            name="hmac_length",
        ),
        # Requete exacte du moteur de rapprochement
        Index(
            "ix_reports_matching",
            "kind",
            "document_number_hmac",
            postgresql_where=text("document_number_hmac IS NOT NULL"),
        ),
        # Requete exacte de la liste publique
        Index("ix_reports_public_list", "is_published", "status", "document_type"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} kind={self.kind}>"


class ReportImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_images"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        index=True,
    )

    storage_path: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)

    # Une photo de piece d'identite ne s'affiche jamais publiquement,
    # mais sert de preuve lors de la verification de propriete
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    report: Mapped[Report] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<ReportImage id={self.id}>"