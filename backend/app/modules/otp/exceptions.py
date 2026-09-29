class OtpError(Exception):
    """Base des erreurs de vérification par code."""


class OtpThrottledError(OtpError):
    """Trop de codes demandés, ou renvoi trop rapproché."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Veuillez patienter avant de redemander un code")
        self.retry_after_seconds = retry_after_seconds


class InvalidOtpError(OtpError):
    """Code inconnu, expiré, déjà utilisé, ou trop d'essais.

    Volontairement une seule erreur : distinguer ces cas dirait à un
    attaquant si un code est encore valide.
    """