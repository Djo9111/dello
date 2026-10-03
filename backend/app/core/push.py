import logging
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("dello.push")


class PushSender(Protocol):
    """Notification push vers un appareil."""

    def send(self, token: str, title: str, body: str) -> bool: ...


class ConsolePushSender:
    """Écrit la notification dans les logs.

    Permet de développer et de tester tout le module sans projet Firebase.
    """

    def send(self, token: str, title: str, body: str) -> bool:
        logger.warning("PUSH (console) vers %s : %s - %s", token[:12], title, body)
        return True


def get_push_sender() -> PushSender:
    if settings.PUSH_PROVIDER == "console":
        return ConsolePushSender()

    raise RuntimeError(f"Fournisseur push inconnu : {settings.PUSH_PROVIDER}")