"""Outils partagés par les tests d'API."""

from app.core.config import settings

from tests.sms_outbox import OUTBOX

API = settings.API_V1_PREFIX
PASSWORD = "Tamarin-Soleil-9"


def create_account(client, phone: str, name: str = "Awa Diop") -> dict:
    """Inscription complète, quel que soit le mode de vérification.

    Retourne l'en-tête d'authentification prêt à l'emploi.
    """
    response = client.post(
        f"{API}/auth/register",
        json={"phone_number": phone, "full_name": name, "password": PASSWORD},
    ).json()

    if not response.get("verification_required"):
        tokens = response["tokens"]
    else:
        code = OUTBOX.last_code()
        tokens = client.post(
            f"{API}/auth/verify", json={"phone_number": phone, "code": code}
        ).json()

    return {"Authorization": f"Bearer {tokens['access_token']}"}


def login(client, phone: str, password: str = PASSWORD) -> dict:
    tokens = client.post(
        f"{API}/auth/login", json={"phone_number": phone, "password": password}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def allow_new_code(db) -> None:
    """Vieillit les codes déjà envoyés pour contourner le délai d'attente.

    Utile quand un test doit réinscrire le même numéro : en usage réel,
    l'utilisateur patienterait une minute.
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from app.core.config import settings
    from app.modules.otp.models import OtpCode

    db.execute(
        update(OtpCode).values(
            created_at=datetime.now(UTC)
            - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS + 5)
        )
    )
    db.commit()