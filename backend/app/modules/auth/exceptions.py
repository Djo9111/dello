class AuthError(Exception):
    """Base des erreurs d'authentification."""


class PhoneAlreadyRegisteredError(AuthError):
    """Un compte existe déjà avec ce numéro."""


class InvalidCredentialsError(AuthError):
    """
    Connexion refusée. Volontairement une seule erreur pour tous les cas
    (numéro inconnu, mauvais mot de passe, compte verrouillé ou désactivé) :
    la réponse ne doit rien révéler sur l'existence ou l'état d'un compte.
    """


class InvalidRefreshTokenError(AuthError):
    """Refresh token inconnu, expiré, révoqué ou réutilisé."""