import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_document_number
from app.modules.claims.verification import hash_answer
from app.modules.reports.exceptions import ReportNotFoundError
from app.modules.reports.masking import mask_owner_name
from app.modules.reports.models import (
    DocumentType,
    Report,
    ReportDocument,
    ReportKind,
    ReportStatus,
)
from app.modules.reports.schemas import ReportCreate, ReportUpdate
from app.modules.users.models import User

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20

MIN_SEARCH_LENGTH = 2
MIN_DOCUMENT_NUMBER_SEARCH = 5

# Un signalement clos (document restitué) sort de la liste publique
PUBLIC_STATUSES = (ReportStatus.OPEN, ReportStatus.MATCHED)


def _with_documents(query):
    """Charge les documents en une requête : sans cela, une liste de 20
    signalements en déclencherait 21."""
    return query.options(selectinload(Report.documents))


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def create_report(db: Session, user: User, data: ReportCreate) -> Report:
    """Les numéros deviennent des empreintes HMAC, le nom est masqué.
    Ni les uns ni l'autre ne sont stockés en clair."""
    report = Report(
        user_id=user.id,
        kind=data.kind,
        circumstance=data.circumstance,
        owner_name_masked=mask_owner_name(data.owner_name) if data.owner_name else None,
        region=data.region,
        commune=data.commune,
        place_detail=data.place_detail,
        occurred_on=data.occurred_on,
        latitude=data.latitude,
        longitude=data.longitude,
        verification_question=data.verification_question,
        verification_answer_hash=(
            hash_answer(data.verification_answer.get_secret_value())
            if data.verification_answer is not None
            else None
        ),
    )

    for document in data.documents:
        report.documents.append(
            ReportDocument(
                document_type=document.document_type,
                document_number_hmac=(
                    hash_document_number(
                        document.document_type.value,
                        document.document_number.get_secret_value(),
                    )
                    if document.document_number is not None
                    else None
                ),
            )
        )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def get_own_report(db: Session, report_id: uuid.UUID, user: User) -> Report:
    """Signalement de l'utilisateur. Erreur identique s'il n'existe pas
    ou s'il appartient à quelqu'un d'autre."""
    report = db.scalar(_with_documents(select(Report).where(Report.id == report_id)))

    if report is None or report.user_id is None or report.user_id != user.id:
        raise ReportNotFoundError()

    return report


def get_public_report(db: Session, report_id: uuid.UUID) -> Report:
    report = db.scalar(_with_documents(select(Report).where(Report.id == report_id)))

    if report is None or not report.is_published or report.status not in PUBLIC_STATUSES:
        raise ReportNotFoundError()

    return report


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------


def _escape_like(value: str) -> str:
    """Neutralise les jokers SQL. Sans cela, une recherche sur % renverrait
    toute la base, et _ remplacerait n'importe quel caractere."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_filter(text: str):
    """Recherche unique sur trois entrees.

    Un numero de document est compare par empreinte HMAC, donc exactement,
    puisque le numero en clair n'existe nulle part en base. Le reste est
    une recherche textuelle sur le lieu et le nom masque.
    """
    clauses = []

    compact = "".join(ch for ch in text if ch.isascii() and ch.isalnum())
    digits = sum(ch.isdigit() for ch in compact)

    if len(compact) >= MIN_DOCUMENT_NUMBER_SEARCH and digits >= 4:
        # Le type du document fait partie du message HMAC : on teste
        # les empreintes de tous les types possibles.
        hmacs = [
            hash_document_number(document_type.value, compact)
            for document_type in DocumentType
        ]
        clauses.append(
            Report.id.in_(
                select(ReportDocument.report_id).where(
                    ReportDocument.document_number_hmac.in_(hmacs)
                )
            )
        )

    pattern = f"%{_escape_like(text)}%"
    clauses.extend(
        [
            Report.commune.ilike(pattern),
            Report.region.ilike(pattern),
            Report.owner_name_masked.ilike(pattern),
        ]
    )

    return or_(*clauses)


# ---------------------------------------------------------------------------
# Listes
# ---------------------------------------------------------------------------


def list_public_reports(
    db: Session,
    *,
    kind: ReportKind | None = None,
    document_type: DocumentType | None = None,
    region: str | None = None,
    search: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> list[Report]:
    query = select(Report).where(
        Report.is_published.is_(True),
        Report.status.in_(PUBLIC_STATUSES),
    )

    if kind is not None:
        query = query.where(Report.kind == kind)

    if document_type is not None:
        # Un signalement apparaît dans chaque famille qu'il contient
        query = query.where(
            Report.id.in_(
                select(ReportDocument.report_id).where(
                    ReportDocument.document_type == document_type
                )
            )
        )

    if region is not None:
        query = query.where(Report.region == region)

    if search is not None:
        cleaned = " ".join(search.split())
        if len(cleaned) >= MIN_SEARCH_LENGTH:
            query = query.where(_search_filter(cleaned))

    query = (
        query.order_by(Report.created_at.desc())
        .limit(min(limit, MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )

    return list(db.scalars(_with_documents(query)))


def list_own_reports(
    db: Session, user: User, *, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
) -> list[Report]:
    query = (
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .limit(min(limit, MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )
    return list(db.scalars(_with_documents(query)))


# ---------------------------------------------------------------------------
# Modification et suppression
# ---------------------------------------------------------------------------


def update_report(db: Session, report: Report, data: ReportUpdate) -> Report:
    """Seuls les champs réellement envoyés sont modifiés : sans exclude_unset,
    les champs absents écraseraient les valeurs existantes avec None."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, report: Report) -> None:
    db.delete(report)
    db.commit()


# ---------------------------------------------------------------------------
# Rapprochement
# ---------------------------------------------------------------------------


def find_potential_matches(db: Session, report: Report) -> list[Report]:
    """Signalements du sens opposé portant au moins un document de même
    empreinte.

    Rapprochement déterministe : un numéro de pièce identifie un document
    de manière unique, donc aucun score de similarité n'est nécessaire.
    """
    hmacs = [
        document.document_number_hmac
        for document in report.documents
        if document.document_number_hmac is not None
    ]
    if not hmacs:
        return []

    opposite = ReportKind.FOUND if report.kind is ReportKind.LOST else ReportKind.LOST

    query = (
        select(Report)
        .where(
            Report.kind == opposite,
            Report.status != ReportStatus.CLOSED,
            Report.id != report.id,
            Report.id.in_(
                select(ReportDocument.report_id).where(
                    ReportDocument.document_number_hmac.in_(hmacs)
                )
            ),
        )
        .order_by(Report.created_at.desc())
    )

    return list(db.scalars(_with_documents(query)))