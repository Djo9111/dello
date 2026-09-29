"""Boîte d'envoi SMS partagée par les tests.

Instance unique, vidée avant chaque test par une fixture de conftest.
Elle évite de passer un objet en paramètre à chaque appel d'aide, alors
que presque tous les tests ont besoin d'un compte vérifié.
"""

import re


class RecordingSmsSender:
    """Garde les messages au lieu de les envoyer.

    Le code n'est stocké que haché en base, donc les tests le lisent ici,
    exactement comme un utilisateur le lirait sur son téléphone.
    """

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, phone_number: str, message: str) -> bool:
        self.messages.append((phone_number, message))
        return True

    def clear(self) -> None:
        self.messages.clear()

    def last_code(self, phone_number: str | None = None) -> str:
        for number, message in reversed(self.messages):
            if phone_number is not None and number != phone_number:
                continue
            found = re.search(r"\b(\d{6})\b", message)
            if found:
                return found.group(1)

        raise AssertionError(f"Aucun code envoyé (messages : {self.messages})")


OUTBOX = RecordingSmsSender()