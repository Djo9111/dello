"""Masquage du nom porté sur un document.

Le nom est masqué une seule fois, à la création du signalement, et stocké
sous cette forme. Il n'est jamais recalculé à l'affichage : un oubli dans
une requête exposerait alors le nom complet.
"""

_VISIBLE_FIRST_PART = 3


def mask_owner_name(full_name: str) -> str:
    """"Modienne GUISSE" devient "Mod... G...".

    Assez pour qu'un propriétaire se reconnaisse, pas assez pour qu'un
    inconnu exploite l'information.
    """
    parts = full_name.split()
    if not parts:
        raise ValueError("Nom vide")

    masked = [f"{parts[0][:_VISIBLE_FIRST_PART]}..."]
    masked.extend(f"{part[0]}..." for part in parts[1:])

    return " ".join(masked)