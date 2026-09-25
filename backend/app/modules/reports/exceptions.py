class ReportError(Exception):
    """Base des erreurs du module signalements."""


class ReportNotFoundError(ReportError):
    """
    Signalement inexistant, non publié, ou appartenant à quelqu'un d'autre.

    Volontairement une seule erreur : répondre "interdit" pour le signalement
    d'un autre confirmerait son existence à qui teste des identifiants.
    """