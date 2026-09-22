from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """
    Base des schémas d'entrée :
    - extra="forbid" : tout champ inconnu est refusé (pas de role="admin" glissé dans la requête)
    - hide_input_in_errors : les valeurs saisies n'apparaissent pas dans le texte des erreurs (logs)
    """

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)