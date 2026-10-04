import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.push import get_push_sender
from app.core.sms import get_sms_sender
from app.modules.notifications.models import (
    DeviceToken,
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from app.modules.users.models import User

logger = logging.getLogger("dello.notifications")

MAX_PAGE_SIZE = 50

# Titre pour le push, message court pour le SMS. Les SMS restent sans
# accents : hors alphabet GSM, un message est facturé double.
MESSAGES: dict[NotificationEvent, tuple[str, str]] = {
    NotificationEvent.CLAIM_RECEIVED: (
        "Nouvelle demande",
        # Formulation neutre : une demande peut venir du proprietaire d'un
        # document trouve, comme de quelqu'un qui detient un document perdu.
        "Dello : vous avez recu une demande de mise en relation sur votre "
        "signalement. Ouvrez l'application pour repondre.",
    ),
    NotificationEvent.CLAIM_APPROVED: (
        "Demande acceptee",
        "Dello : votre demande a ete acceptee. "
        "Le contact est disponible dans l'application.",
    ),
    NotificationEvent.CLAIM_REJECTED: (
        "Demande refusee",
        "Dello : votre demande n'a pas ete retenue par le declarant.",
    ),
    NotificationEvent.MATCH_FOUND: (
        "Document retrouve",
        "Dello : un document correspondant au votre vient d'etre signale. "
        "Ouvrez l'application pour le voir.",
    ),
}


def notify(
    db: Session,
    user: User,
    event: NotificationEvent,
    *,
    target_id: uuid.UUID | None = None,
    dedup_key: str | None = None,
) -> NotificationLog | None:
    """Prévient un utilisateur, par push si un appareil est inscrit,
    par SMS sinon.

    Retourne None si le message a déjà été envoyé. Une notification ne
    doit jamais faire échouer l'action métier qui l'a déclenchée, donc
    toute erreur d'envoi est enregistrée puis ignorée.
    """
    if dedup_key is not None and _already_sent(db, dedup_key):
        return None

    title, body = MESSAGES[event]
    tokens = list(
        db.scalars(select(DeviceToken.token).where(DeviceToken.user_id == user.id))
    )

    if tokens:
        channel = NotificationChannel.PUSH
        sent = _send_push(tokens, title, body)
    elif user.is_phone_verified:
        # Sans appareil inscrit, le SMS reste le seul moyen d'atteindre
        # quelqu'un qui n'a pas ouvert l'application depuis des jours.
        channel = NotificationChannel.SMS
        sent = _send_sms(user.phone_number, body)
    else:
        # Aucun envoi externe possible : la notification attend dans
        # l'application, où elle sera lue à la prochaine ouverture.
        channel = NotificationChannel.IN_APP
        sent = True

    entry = NotificationLog(
        user_id=user.id,
        event=event,
        channel=channel,
        status=NotificationStatus.SENT if sent else NotificationStatus.FAILED,
        target_id=target_id,
        dedup_key=dedup_key,
    )
    db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        # Deux envois simultanés pour le même événement
        db.rollback()
        return None

    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Boîte de réception
# ---------------------------------------------------------------------------


def list_notifications(
    db: Session, user: User, *, limit: int = 30, offset: int = 0
) -> list[NotificationLog]:
    """Notifications de l'utilisateur, de la plus récente à la plus ancienne.

    Toute notification est enregistrée, quel que soit le canal utilisé pour
    la faire sortir du serveur : la boîte de réception reste complète même
    si un envoi externe a échoué.
    """
    query = (
        select(NotificationLog)
        .where(NotificationLog.user_id == user.id)
        .order_by(NotificationLog.created_at.desc())
        .limit(min(limit, MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )
    return list(db.scalars(query))


def count_unread(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count())
        .select_from(NotificationLog)
        .where(
            NotificationLog.user_id == user.id,
            NotificationLog.read_at.is_(None),
        )
    )


def mark_as_read(db: Session, user: User, notification_id: uuid.UUID) -> bool:
    """Retourne faux si la notification n'existe pas ou appartient à
    quelqu'un d'autre : les deux cas se traitent de la même façon."""
    notification = db.get(NotificationLog, notification_id)

    if notification is None or notification.user_id != user.id:
        return False

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()

    return True


def mark_all_as_read(db: Session, user: User) -> int:
    result = db.execute(
        update(NotificationLog)
        .where(
            NotificationLog.user_id == user.id,
            NotificationLog.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return result.rowcount or 0

def register_device(
    db: Session, user: User, token: str, platform: str
) -> DeviceToken:
    """Inscrit un appareil. Un même jeton peut changer de compte quand
    deux personnes utilisent le même téléphone."""
    existing = db.scalar(select(DeviceToken).where(DeviceToken.token == token))

    if existing is not None:
        existing.user_id = user.id
        existing.platform = platform
        existing.last_seen_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        return existing

    device = DeviceToken(
        user_id=user.id,
        token=token,
        platform=platform,
        last_seen_at=datetime.now(UTC),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def unregister_device(db: Session, user: User, token: str) -> None:
    """À la déconnexion : sans cela, le téléphone continuerait de
    recevoir les notifications du compte précédent."""
    device = db.scalar(
        select(DeviceToken).where(
            DeviceToken.token == token, DeviceToken.user_id == user.id
        )
    )
    if device is None:
        return

    db.delete(device)
    db.commit()


# ---------------------------------------------------------------------------
# Interne
# ---------------------------------------------------------------------------


def _already_sent(db: Session, dedup_key: str) -> bool:
    return (
        db.scalar(
            select(NotificationLog.id).where(NotificationLog.dedup_key == dedup_key)
        )
        is not None
    )


def _send_push(tokens: list[str], title: str, body: str) -> bool:
    sender = get_push_sender()
    results = []

    for token in tokens:
        try:
            results.append(sender.send(token, title, body))
        except Exception:
            logger.exception("Echec d'envoi push")
            results.append(False)

    return any(results)


def _send_sms(phone_number: str, body: str) -> bool:
    try:
        return get_sms_sender().send(phone_number, body)
    except Exception:
        logger.exception("Echec d'envoi SMS")
        return False