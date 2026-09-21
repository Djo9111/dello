"""Registre des modèles : importe tout pour qu'Alembic les détecte."""

from app.shared.base_model import Base
from app.modules.users import models as users_models  # noqa: F401
from app.modules.reports import models as reports_models  # noqa: F401

__all__ = ["Base"]