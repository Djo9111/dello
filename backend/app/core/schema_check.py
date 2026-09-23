from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.database import engine

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


class DatabaseSchemaError(RuntimeError):
    """La base n'est pas à la dernière révision Alembic."""


def verify_database_schema() -> None:
    """
    Compare la révision appliquée en base à la dernière révision du code.
    Mieux vaut refuser de démarrer que servir des erreurs 500 sur une
    table manquante.
    """
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    expected = script.get_current_head()

    with engine.connect() as connection:
        applied = MigrationContext.configure(connection).get_current_revision()

    if applied != expected:
        raise DatabaseSchemaError(
            f"Base non à jour : révision appliquée {applied or 'aucune'}, "
            f"attendue {expected}. Lancez : alembic upgrade head"
        )