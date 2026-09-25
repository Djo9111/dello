import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.reports import service
from app.modules.reports.models import DocumentType, ReportKind
from app.modules.reports.schemas import (
    SENEGAL_REGIONS,
    ReportCreate,
    ReportPublic,
    ReportRead,
    ReportUpdate,
)

router = APIRouter(prefix="/reports", tags=["Signalements"])


def _check_region(region: str | None) -> str | None:
    if region is None:
        return None
    match = next((r for r in SENEGAL_REGIONS if r.lower() == region.lower()), None)
    if match is None:
        raise HTTPException(
            status_code=422,
            detail=[{"field": "region", "message": "Région du Sénégal inconnue"}],
        )
    return match


# ---------------------------------------------------------------------------
# Mes signalements (avant /{report_id}, sinon "me" serait lu comme un UUID)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=list[ReportRead])
def list_my_reports(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    reports = service.list_own_reports(db, current_user, limit=limit, offset=offset)
    return [ReportRead.from_report(report) for report in reports]


@router.get("/me/{report_id}", response_model=ReportRead)
def read_my_report(report_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    return ReportRead.from_report(service.get_own_report(db, report_id, current_user))


@router.get("/me/{report_id}/matches", response_model=list[ReportPublic])
def list_matches(report_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    """Signalements du sens opposé portant le même numéro de document."""
    report = service.get_own_report(db, report_id, current_user)
    return service.find_potential_matches(db, report)


# ---------------------------------------------------------------------------
# Liste visible par les utilisateurs connectés
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ReportPublic])
def list_reports(
    current_user: CurrentUser,
    db: DbSession,
    kind: ReportKind | None = None,
    document_type: DocumentType | None = None,
    region: str | None = Query(None, max_length=60),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    return service.list_public_reports(
        db,
        kind=kind,
        document_type=document_type,
        region=_check_region(region),
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportPublic)
def read_report(report_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    return service.get_public_report(db, report_id)


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.REPORT_CREATE_RATE_LIMIT)
def create_report(
    request: Request,
    data: ReportCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    return ReportRead.from_report(service.create_report(db, current_user, data))


@router.patch("/{report_id}", response_model=ReportRead)
def update_report(
    report_id: uuid.UUID,
    data: ReportUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    report = service.get_own_report(db, report_id, current_user)
    return ReportRead.from_report(service.update_report(db, report, data))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    service.delete_report(db, service.get_own_report(db, report_id, current_user))