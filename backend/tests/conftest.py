import os

os.environ["POSTGRES_DB"] = "dello_test"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def guard_test_database():
    """Empêche les tests de tourner sur une autre base que la base de test."""
    if not settings.POSTGRES_DB.endswith("_test"):
        pytest.exit(
            f"Base '{settings.POSTGRES_DB}' refusée : les tests exigent une base *_test",
            returncode=1,
        )
    yield


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session