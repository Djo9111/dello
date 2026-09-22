import os
from pathlib import Path

os.environ["POSTGRES_DB"] = "dello_test"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Vérifie qu'on est sur la base de test, puis la reconstruit via Alembic."""
    if not settings.POSTGRES_DB.endswith("_test"):
        pytest.exit(
            f"Base '{settings.POSTGRES_DB}' refusée : les tests exigent une base *_test",
            returncode=1,
        )

    alembic_config = Config(str(ALEMBIC_INI))
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    yield


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session
    _truncate_all_tables()


@pytest.fixture
def client():
    """Client HTTP de test. Rate limiting désactivé par défaut (voir rate_limited_client)."""
    limiter.reset()
    limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    limiter.enabled = True
    _truncate_all_tables()


@pytest.fixture
def rate_limited_client(client):
    limiter.enabled = True
    yield client


def _truncate_all_tables() -> None:
    """Vide toutes les tables de l'app après chaque test."""
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    if table_names:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {table_names} CASCADE"))