import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.modules.reports.models import DocumentType, ReportKind, ReportStatus
from app.shared.schemas import StrictModel
from app.shared.validators import normalize_full_name

# Les 14 régions administratives du Sénégal
SENEGAL_REGIONS = (
    "Dakar", "Diourbel", "Fatick", "Kaffrine", "Kaolack", "Kedougou",
    "Kolda", "Louga", "Matam", "Saint-Louis", "Sedhiou", "Tambacounda",
    "Thies", "Ziguinchor",
)

MAX_REPORT_AGE_DAYS = 365 * 3
MIN_DOCUMENT_NUMBER_LENGTH = 4
MAX_DOCUMENT_NUMBER_LENGTH = 30


class ReportCreate(StrictModel):
    kind: ReportKind
    document_type: DocumentType

    # SecretStr : le numéro ne doit apparaître ni dans les logs ni dans un repr.
    # Il est transformé en empreinte HMAC par le service et jamais stocké en clair.
    document_number: SecretStr | None = None

    # Nom porté sur la pièce. Masqué avant stockage, jamais conservé en entier.
    owner_name: str | None = Field(default=None, max_length=150)

    region: str = Field(max_length=60)
    commune: str | None = Field(default=None, max_length=80)
    place_detail: str | None = Field(default=None, max_length=255)
    occurred_on: date | None = None

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str) -> str:
        match = next(
            (region for region in SENEGAL_REGIONS if region.lower() == value.strip().lower()),
            None,
        )
        if match is None:
            raise ValueError("Région du Sénégal inconnue")
        return match

    @field_validator("commune", "place_detail")
    @classmethod
    def clean_free_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("owner_name")
    @classmethod
    def validate_owner_name(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return normalize_full_name(value)

    @field_validator("document_number")
    @classmethod
    def validate_document_number(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None

        raw = value.get_secret_value().strip()
        if not raw:
            return None

        compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum())
        if not MIN_DOCUMENT_NUMBER_LENGTH <= len(compact) <= MAX_DOCUMENT_NUMBER_LENGTH:
            raise ValueError(
                f"Le numéro doit contenir entre {MIN_DOCUMENT_NUMBER_LENGTH} "
                f"et {MAX_DOCUMENT_NUMBER_LENGTH} caractères alphanumériques"
            )
        return value

    @field_validator("occurred_on")
    @classmethod
    def validate_occurred_on(cls, value: date | None) -> date | None:
        if value is None:
            return None

        today = datetime.now(UTC).date()
        if value > today:
            raise ValueError("La date ne peut pas être dans le futur")
        if (today - value).days > MAX_REPORT_AGE_DAYS:
            raise ValueError("La date est trop ancienne")
        return value


class ReportUpdate(StrictModel):
    """Champs modifiables après création. Ni le type ni le numéro : les
    changer reviendrait à déclarer un autre document."""

    commune: str | None = Field(default=None, max_length=80)
    place_detail: str | None = Field(default=None, max_length=255)
    is_published: bool | None = None

    @field_validator("commune", "place_detail")
    @classmethod
    def clean_free_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class ReportPublic(BaseModel):
    """Ce que tout le monde peut voir. Ni place_detail (lieu précis),
    ni indication sur le numéro du document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ReportKind
    document_type: DocumentType
    owner_name_masked: str | None
    region: str
    commune: str | None
    occurred_on: date | None
    status: ReportStatus
    created_at: datetime


class ReportRead(ReportPublic):
    """Vue du propriétaire du signalement : ajoute le lieu précis et la
    publication. Le numéro reste absent, seule sa présence est indiquée."""

    place_detail: str | None
    is_published: bool
    has_document_number: bool

    @classmethod
    def from_report(cls, report) -> "ReportRead":
        return cls(
            id=report.id,
            kind=report.kind,
            document_type=report.document_type,
            owner_name_masked=report.owner_name_masked,
            region=report.region,
            commune=report.commune,
            occurred_on=report.occurred_on,
            status=report.status,
            created_at=report.created_at,
            place_detail=report.place_detail,
            is_published=report.is_published,
            has_document_number=report.document_number_hmac is not None,
        )