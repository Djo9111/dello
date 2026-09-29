import logging
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("dello.sms")


class SmsSender(Protocol):
    """Envoi d'un SMS. L'implémentation change selon le fournisseur,
    le reste du code ne le sait pas."""

    def send(self, phone_number: str, message: str) -> bool: ...


class ConsoleSmsSender:
    """Écrit le message dans les logs au lieu de l'envoyer.

    Sert au développement et aux tests : tout le module fonctionne sans
    compte chez un opérateur et sans dépenser un franc.
    """

    def send(self, phone_number: str, message: str) -> bool:
        logger.warning("SMS (console) vers %s : %s", phone_number, message)
        return True


def get_sms_sender() -> SmsSender:
    if settings.SMS_PROVIDER == "console":
        return ConsoleSmsSender()

    raise RuntimeError(f"Fournisseur SMS inconnu : {settings.SMS_PROVIDER}")