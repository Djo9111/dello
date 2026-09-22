class UserError(Exception):
    """Base des erreurs du module utilisateurs."""


class WrongPasswordError(UserError):
    """Mot de passe incorrect lors d'une action sensible (suppression de compte)."""