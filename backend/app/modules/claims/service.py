import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.claims.exceptions import (
    ClaimAlreadyExistsError,
    ClaimAlreadyResolvedError,
    ClaimNotAllowedError,
    ClaimNotFoundError,
    NoVerificationQuestionError,
    WrongVerificationAnswerError,
)
from app.modules.claims.models import Claim, ClaimStatus
from app.modules.claims.verification import check_answer
from app.modules.reports.models import Report, ReportStatus
from app.modules.users.models import User

# Au-delà, la vérification automatique est abandonnée et le déclarant tranche.
# Une réponse peut être mal orthographiée par le vrai propriétaire : on ne
# ferme donc jamais définitivement la porte, on repasse la main à l'humain.
MAX_ANSWER_ATTEMPTS = 3


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def create_claim(
    db: Session,
    report: Report,
    claimant: User,
    *,
    message: str | None = None,
    answer: str | None = None,
) -> Claim:
    """Demande de mise en relation.

    Bonne réponse à la question de vérification : acceptée immédiatement.
    Sinon : en attente de la décision du déclarant.
    """
    if report.user_id is None:
        raise ClaimNotAllowedError("Ce signalement n'a plus de déclarant")
    if report.user_id == claimant.id:
        raise ClaimNotAllowedError("Vous ne pouvez pas revendiquer votre signalement")
    if report.status is ReportStatus.CLOSED or not report.is_published:
        raise ClaimNotAllowedError("Ce signalement n'est plus disponible")

    claim = Claim(report_id=report.id, claimant_id=claimant.id, message=message)

    if answer is not None and report.verification_answer_hash is not None:
        if check_answer(answer, report.verification_answer_hash):
            claim.status = ClaimStatus.VERIFIED
            claim.resolved_at = _now()
        else:
            claim.answer_attempts = 1

    db.add(claim)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ClaimAlreadyExistsError() from exc

    if claim.status is ClaimStatus.VERIFIED:
        _mark_report_matched(db, report)

    db.refresh(claim)
    return claim


# ---------------------------------------------------------------------------
# Vérification après coup
# ---------------------------------------------------------------------------


def answer_verification(db: Session, claim: Claim, answer: str) -> Claim:
    """Nouvelle tentative de réponse sur une demande en attente."""
    if claim.status is not ClaimStatus.PENDING:
        raise ClaimAlreadyResolvedError()

    report = db.get(Report, claim.report_id)
    if report is None or report.verification_answer_hash is None:
        raise NoVerificationQuestionError()

    if claim.answer_attempts >= MAX_ANSWER_ATTEMPTS:
        # Plus de vérification automatique : le déclarant décide
        raise WrongVerificationAnswerError()

    if not check_answer(answer, report.verification_answer_hash):
        claim.answer_attempts += 1
        db.commit()
        raise WrongVerificationAnswerError()

    claim.status = ClaimStatus.VERIFIED
    claim.resolved_at = _now()
    db.commit()

    _mark_report_matched(db, report)
    db.refresh(claim)
    return claim


# ---------------------------------------------------------------------------
# Décisions
# ---------------------------------------------------------------------------


def approve_claim(db: Session, claim: Claim) -> Claim:
    """Acceptation manuelle par le déclarant du signalement."""
    if claim.status is not ClaimStatus.PENDING:
        raise ClaimAlreadyResolvedError()

    claim.status = ClaimStatus.VERIFIED
    claim.resolved_at = _now()
    db.commit()

    report = db.get(Report, claim.report_id)
    if report is not None:
        _mark_report_matched(db, report)

    db.refresh(claim)
    return claim


def reject_claim(db: Session, claim: Claim) -> Claim:
    if claim.status is not ClaimStatus.PENDING:
        raise ClaimAlreadyResolvedError()

    claim.status = ClaimStatus.REJECTED
    claim.resolved_at = _now()
    db.commit()
    db.refresh(claim)
    return claim


def withdraw_claim(db: Session, claim: Claim) -> Claim:
    """Annulation par le demandeur, y compris après acceptation :
    la mise en relation prend fin et les contacts ne sont plus visibles."""
    if claim.status in (ClaimStatus.REJECTED, ClaimStatus.WITHDRAWN):
        raise ClaimAlreadyResolvedError()

    claim.status = ClaimStatus.WITHDRAWN
    claim.resolved_at = _now()
    db.commit()
    db.refresh(claim)
    return claim


def close_report(db: Session, report: Report) -> Report:
    """Document restitué : le signalement sort de la liste publique et
    toutes les demandes encore en attente sont refusées."""
    report.status = ReportStatus.CLOSED

    db.execute(
        update(Claim)
        .where(Claim.report_id == report.id, Claim.status == ClaimStatus.PENDING)
        .values(status=ClaimStatus.REJECTED, resolved_at=_now())
    )

    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def get_claim_for_participant(db: Session, claim_id: uuid.UUID, user: User) -> Claim:
    """Demande visible par le demandeur ou par le déclarant du signalement.
    Même erreur dans tous les autres cas."""
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimNotFoundError()

    report = db.get(Report, claim.report_id)
    if report is None:
        raise ClaimNotFoundError()

    if claim.claimant_id != user.id and report.user_id != user.id:
        raise ClaimNotFoundError()

    return claim


def get_claim_as_report_owner(db: Session, claim_id: uuid.UUID, user: User) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimNotFoundError()

    report = db.get(Report, claim.report_id)
    if report is None or report.user_id != user.id:
        raise ClaimNotFoundError()

    return claim


def get_claim_as_claimant(db: Session, claim_id: uuid.UUID, user: User) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None or claim.claimant_id != user.id:
        raise ClaimNotFoundError()

    return claim


def list_my_claims(db: Session, user: User) -> list[Claim]:
    query = (
        select(Claim)
        .where(Claim.claimant_id == user.id)
        .order_by(Claim.created_at.desc())
    )
    return list(db.scalars(query))


def list_claims_on_my_reports(db: Session, user: User) -> list[Claim]:
    query = (
        select(Claim)
        .join(Report, Report.id == Claim.report_id)
        .where(Report.user_id == user.id)
        .order_by(Claim.created_at.desc())
    )
    return list(db.scalars(query))


def get_contact(db: Session, claim: Claim, user: User) -> User:
    """Coordonnées de l'autre partie.

    Le contact n'est jamais exposé par une simple correspondance : il faut
    une demande acceptée. Sinon, déclarer un numéro de pièce au hasard
    suffirait à récupérer le téléphone de gens de bonne foi.
    """
    if claim.status is not ClaimStatus.VERIFIED:
        raise ClaimNotFoundError()

    report = db.get(Report, claim.report_id)
    if report is None:
        raise ClaimNotFoundError()

    if user.id == claim.claimant_id:
        other_id = report.user_id
    elif user.id == report.user_id:
        other_id = claim.claimant_id
    else:
        raise ClaimNotFoundError()

    other = db.get(User, other_id) if other_id is not None else None
    if other is None:
        raise ClaimNotFoundError()

    return other


# ---------------------------------------------------------------------------
# Interne
# ---------------------------------------------------------------------------


def _mark_report_matched(db: Session, report: Report) -> None:
    if report.status is ReportStatus.OPEN:
        report.status = ReportStatus.MATCHED
        db.commit()