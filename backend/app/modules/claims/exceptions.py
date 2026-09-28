class ClaimError(Exception):
    """Base des erreurs du module revendications."""


class ClaimNotFoundError(ClaimError):
    """Demande inexistante ou ne concernant pas cet utilisateur."""


class ClaimNotAllowedError(ClaimError):
    """Signalement non revendicable : le sien, sans propriétaire, ou clôturé."""


class ClaimAlreadyExistsError(ClaimError):
    """Une demande existe déjà pour ce signalement et cette personne."""


class ClaimAlreadyResolvedError(ClaimError):
    """La demande a déjà été acceptée, refusée ou annulée."""


class WrongVerificationAnswerError(ClaimError):
    """Réponse incorrecte à la question de vérification."""


class NoVerificationQuestionError(ClaimError):
    """Ce signalement ne comporte pas de question de vérification."""