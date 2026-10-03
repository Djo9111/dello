"""Déclenchement des notifications depuis les routes.

Ces fonctions ouvrent leur propre session et sont appelées en tâche de
fond : l'API répond sans attendre l'envoi, et une panne de notification
ne fait jamais échouer l'action de l'utilisateur.
"""

import logging
import uuid

from app.core.database import SessionLocal
from app.modules.claims.models import Claim, ClaimStatus
from app.modules.notifications import service
from app.modules.notifications.models import NotificationEvent
from app.modules.reports import service as reports_service
from app.modules.reports.models import Report
from app.modules.users.models import User

logger = logging.getLogger("dello.notifications")


def on_claim_created(claim_id: uuid.UUID) -> None:
    """Prévient le déclarant du signalement qu'une demande est arrivée."""
    with SessionLocal() as db:
        try:
            claim = db.get(Claim, claim_id)
            if claim is None:
                return

            report = db.get(Report, claim.report_id)
            owner = db.get(User, report.user_id) if report else None
            if owner is None:
                return

            service.notify(
                db,
                owner,
                NotificationEvent.CLAIM_RECEIVED,
                target_id=claim.id,
                dedup_key=f"claim_received:{claim.id}",
            )
        except Exception:
            logger.exception("Notification de demande impossible")


def on_claim_resolved(claim_id: uuid.UUID) -> None:
    """Prévient le demandeur de la décision prise."""
    with SessionLocal() as db:
        try:
            claim = db.get(Claim, claim_id)
            if claim is None or claim.status is ClaimStatus.PENDING:
                return

            claimant = db.get(User, claim.claimant_id)
            if claimant is None:
                return

            if claim.status is ClaimStatus.VERIFIED:
                event = NotificationEvent.CLAIM_APPROVED
            elif claim.status is ClaimStatus.REJECTED:
                event = NotificationEvent.CLAIM_REJECTED
            else:
                return  # retrait par le demandeur lui-même

            service.notify(
                db,
                claimant,
                event,
                target_id=claim.id,
                dedup_key=f"{event.value}:{claim.id}",
            )
        except Exception:
            logger.exception("Notification de decision impossible")


def on_report_created(report_id: uuid.UUID) -> None:
    """Cherche les correspondances et prévient les deux parties.

    C'est ici que Dello travaille pour l'utilisateur : personne n'a
    besoin d'ouvrir l'application pour découvrir que sa pièce a été
    retrouvée.
    """
    with SessionLocal() as db:
        try:
            report = db.get(Report, report_id)
            if report is None:
                return

            matches = reports_service.find_potential_matches(db, report)
            if not matches:
                return

            new_owner = db.get(User, report.user_id) if report.user_id else None

            for match in matches:
                # Une clé stable pour la paire, quel que soit l'ordre de
                # déclaration : le second signalement ne renotifie pas.
                pair = ":".join(sorted([str(report.id), str(match.id)]))

                if new_owner is not None:
                    service.notify(
                        db,
                        new_owner,
                        NotificationEvent.MATCH_FOUND,
                        target_id=match.id,
                        dedup_key=f"match:{pair}:{new_owner.id}",
                    )

                other = db.get(User, match.user_id) if match.user_id else None
                if other is not None:
                    service.notify(
                        db,
                        other,
                        NotificationEvent.MATCH_FOUND,
                        target_id=report.id,
                        dedup_key=f"match:{pair}:{other.id}",
                    )
        except Exception:
            logger.exception("Notification de correspondance impossible")