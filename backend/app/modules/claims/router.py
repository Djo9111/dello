import uuid

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.claims import service
from app.modules.claims.schemas import ClaimAnswer, ClaimRead, ContactRead

router = APIRouter(prefix="/claims", tags=["Revendications"])


@router.get("/mine", response_model=list[ClaimRead])
def list_my_claims(current_user: CurrentUser, db: DbSession):
    """Demandes que j'ai envoyées."""
    return service.list_my_claims(db, current_user)


@router.get("/received", response_model=list[ClaimRead])
def list_received_claims(current_user: CurrentUser, db: DbSession):
    """Demandes reçues sur mes signalements."""
    return service.list_claims_on_my_reports(db, current_user)


@router.get("/{claim_id}", response_model=ClaimRead)
def read_claim(claim_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    return service.get_claim_for_participant(db, claim_id, current_user)


@router.get("/{claim_id}/contact", response_model=ContactRead)
def read_contact(claim_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    """Coordonnées de l'autre partie. Uniquement sur une demande acceptée."""
    claim = service.get_claim_for_participant(db, claim_id, current_user)
    return service.get_contact(db, claim, current_user)


@router.post("/{claim_id}/answer", response_model=ClaimRead)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def answer_verification(
    request: Request,
    claim_id: uuid.UUID,
    data: ClaimAnswer,
    current_user: CurrentUser,
    db: DbSession,
):
    """Nouvelle tentative de réponse à la question de vérification."""
    claim = service.get_claim_as_claimant(db, claim_id, current_user)
    return service.answer_verification(db, claim, data.answer.get_secret_value())


@router.post("/{claim_id}/approve", response_model=ClaimRead)
def approve_claim(claim_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    """Acceptation par le déclarant du signalement."""
    claim = service.get_claim_as_report_owner(db, claim_id, current_user)
    return service.approve_claim(db, claim)


@router.post("/{claim_id}/reject", response_model=ClaimRead)
def reject_claim(claim_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    claim = service.get_claim_as_report_owner(db, claim_id, current_user)
    return service.reject_claim(db, claim)


@router.post("/{claim_id}/withdraw", response_model=ClaimRead)
def withdraw_claim(claim_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    """Annulation par le demandeur. Coupe la mise en relation."""
    claim = service.get_claim_as_claimant(db, claim_id, current_user)
    return service.withdraw_claim(db, claim)