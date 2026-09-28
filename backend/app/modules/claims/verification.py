import unicodedata

from app.core.security import hash_password, verify_password

MAX_ANSWER_LENGTH = 100


def normalize_answer(answer: str) -> str:
    """Compare sur le fond, pas sur la forme : casse, accents, ponctuation
    et espaces multiples sont neutralisés. "12 Juin 1995" et "12 juin 1995"
    sont la même réponse."""
    decomposed = unicodedata.normalize("NFKD", answer.lower())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    kept = [ch if ch.isalnum() else " " for ch in without_accents]
    return " ".join("".join(kept).split())


def hash_answer(answer: str) -> str:
    """Haché avec Argon2, comme un mot de passe : une réponse est une donnée
    à faible entropie, un hachage rapide se casserait par dictionnaire."""
    normalized = normalize_answer(answer)
    if not normalized:
        raise ValueError("Réponse vide")
    return hash_password(normalized[:MAX_ANSWER_LENGTH])


def check_answer(answer: str, answer_hash: str) -> bool:
    normalized = normalize_answer(answer)
    if not normalized:
        return False
    is_valid, _ = verify_password(normalized[:MAX_ANSWER_LENGTH], answer_hash)
    return is_valid