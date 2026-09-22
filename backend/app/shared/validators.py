import re

_SEPARATORS = re.compile(r"[\s.\-()]")
_SENEGAL_MOBILE = re.compile(r"(?:\+221|00221|221)?(7[0-9]{8})")
_NAME_EXTRA_CHARS = {" ", "-", "'", "’"}


def normalize_senegal_mobile(value: str) -> str:
    """Accepte les formats courants et retourne le format E.164 : +221XXXXXXXXX."""
    compact = _SEPARATORS.sub("", value)
    match = _SENEGAL_MOBILE.fullmatch(compact)
    if match is None:
        raise ValueError("Numéro de mobile sénégalais invalide")
    return f"+221{match.group(1)}"


def normalize_full_name(value: str) -> str:
    """Espaces normalisés, lettres (accents compris), espaces, tirets et apostrophes."""
    name = " ".join(value.split())

    if not 2 <= len(name) <= 100:
        raise ValueError("Le nom doit contenir entre 2 et 100 caractères")
    if not all(ch.isalpha() or ch in _NAME_EXTRA_CHARS for ch in name):
        raise ValueError("Le nom contient des caractères non autorisés")
    if sum(ch.isalpha() for ch in name) < 2:
        raise ValueError("Le nom doit contenir au moins 2 lettres")

    return name