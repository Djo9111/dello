import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import fake_password_verification, hash_password, verify_password
from app.core.sms import get_sms_sender
from app.modules.otp.exceptions import InvalidOtpError, OtpThrottledError
from app.modules.otp.models import OtpCode, OtpPurpose, PendingRegistration

CODE_LENGTH = 6


def _now() -> datetime:
    return datetime.now(UTC)


def generate_code() -> str:
    """Six chiffres tirés du générateur cryptographique. random ordinaire
    est prévisible à partir de quelques tirages observés."""
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


# ---------------------------------------------------------------------------
# Limitation des envois
# ---------------------------------------------------------------------------


def check_can_send(db: Session, phone_number: str, purpose: OtpPurpose) -> None:
    """Deux garde-fous : un délai entre deux codes, et un plafond horaire.

    Sans eux, un numéro pourrait être inondé de SMS, aux frais de Dello et
    au détriment de son propriétaire.
    """
    now = _now()

    last = db.scalar(
        select(OtpCode)
        .where(OtpCode.phone_number == phone_number, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )

    if last is not None:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            raise OtpThrottledError(
                int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
            )

    sent_last_hour = db.scalar(
        select(func.count())
        .select_from(OtpCode)
        .where(
            OtpCode.phone_number == phone_number,
            OtpCode.purpose == purpose,
            OtpCode.created_at > now - timedelta(hours=1),
        )
    )

    if sent_last_hour >= settings.OTP_MAX_PER_HOUR:
        raise OtpThrottledError(3600)


# ---------------------------------------------------------------------------
# Émission et vérification
# ---------------------------------------------------------------------------


def issue_code(db: Session, phone_number: str, purpose: OtpPurpose) -> str:
    """Crée un code, invalide les précédents et l'envoie.

    Retourne le code en clair pour les tests uniquement : l'appelant ne
    doit jamais le renvoyer au client.
    """
    now = _now()
    code = generate_code()

    # Un seul code valide à la fois. Les anciens sont marqués consommés
    # plutôt que supprimés : ils restent inutilisables, mais comptent dans
    # le plafond horaire, qui serait sinon toujours à un.
    db.execute(
        update(OtpCode)
        .where(
            OtpCode.phone_number == phone_number,
            OtpCode.purpose == purpose,
            OtpCode.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    db.add(
        OtpCode(
            phone_number=phone_number,
            purpose=purpose,
            code_hash=hash_password(code),
            expires_at=now + timedelta(minutes=settings.OTP_CODE_TTL_MINUTES),
        )
    )
    db.commit()

    get_sms_sender().send(
        phone_number,
        f"Dello : votre code de verification est {code}. "
        f"Il expire dans {settings.OTP_CODE_TTL_MINUTES} minutes.",
    )

    return code


def verify_code(db: Session, phone_number: str, code: str, purpose: OtpPurpose) -> None:
    """Lève InvalidOtpError si le code ne convient pas, pour quelque
    raison que ce soit."""
    now = _now()

    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.phone_number == phone_number,
            OtpCode.purpose == purpose,
            OtpCode.consumed_at.is_(None),
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )

    if otp is None:
        # Même coût en temps qu'une vérification réelle
        fake_password_verification()
        db.rollback()
        raise InvalidOtpError()

    if otp.expires_at <= now or otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        fake_password_verification()
        db.rollback()
        raise InvalidOtpError()

    is_valid, _ = verify_password(code, otp.code_hash)

    if not is_valid:
        otp.attempts += 1
        db.commit()
        raise InvalidOtpError()

    otp.consumed_at = now
    db.commit()


# ---------------------------------------------------------------------------
# Inscriptions en attente
# ---------------------------------------------------------------------------


def save_pending_registration(
    db: Session, phone_number: str, full_name: str, password: str
) -> PendingRegistration:
    """Remplace toute inscription en attente pour ce numéro : la dernière
    demande est celle qui compte."""
    db.execute(
        delete(PendingRegistration).where(
            PendingRegistration.phone_number == phone_number
        )
    )

    pending = PendingRegistration(
        phone_number=phone_number,
        full_name=full_name,
        hashed_password=hash_password(password),
        expires_at=_now() + timedelta(hours=1),
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending


def get_pending_registration(db: Session, phone_number: str) -> PendingRegistration | None:
    pending = db.scalar(
        select(PendingRegistration).where(
            PendingRegistration.phone_number == phone_number
        )
    )

    if pending is None or pending.expires_at <= _now():
        return None

    return pending


def delete_pending_registration(db: Session, phone_number: str) -> None:
    db.execute(
        delete(PendingRegistration).where(
            PendingRegistration.phone_number == phone_number
        )
    )
    db.commit()


def purge_expired(db: Session) -> int:
    """Nettoyage des codes et inscriptions périmés, appelé à chaque envoi :
    pas besoin d'une tâche planifiée pour ce volume."""
    now = _now()

    codes = db.execute(
        delete(OtpCode).where(OtpCode.expires_at < now - timedelta(hours=1))
    )
    pendings = db.execute(
        delete(PendingRegistration).where(PendingRegistration.expires_at < now)
    )
    db.commit()

    return (codes.rowcount or 0) + (pendings.rowcount or 0)