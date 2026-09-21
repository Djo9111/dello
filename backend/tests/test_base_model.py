import uuid

import pytest
from sqlalchemy import MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import engine
from app.shared.base_model import (
    NAMING_CONVENTION,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class IsolatedBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class SampleItem(UUIDPrimaryKeyMixin, TimestampMixin, IsolatedBase):
    __tablename__ = "sample_items"

    name: Mapped[str] = mapped_column(String(50))


@pytest.fixture
def sample_table():
    IsolatedBase.metadata.create_all(engine)
    yield
    IsolatedBase.metadata.drop_all(engine)


@pytest.fixture
def session(sample_table, db_session):
    """La table est créée avant la session, et supprimée après sa fermeture."""
    yield db_session


def test_id_is_uuid4(session):
    item = SampleItem(name="essai")
    session.add(item)
    session.commit()

    assert isinstance(item.id, uuid.UUID)
    assert item.id.version == 4


def test_ids_are_unique(session):
    items = [SampleItem(name=f"item {i}") for i in range(50)]
    session.add_all(items)
    session.commit()

    assert len({item.id for item in items}) == 50


def test_timestamps_are_timezone_aware(session):
    item = SampleItem(name="essai")
    session.add(item)
    session.commit()

    assert item.created_at.tzinfo is not None
    assert item.updated_at.tzinfo is not None


def test_updated_at_changes_on_update(session):
    item = SampleItem(name="avant")
    session.add(item)
    session.commit()

    created = item.created_at
    first_updated = item.updated_at

    item.name = "apres"
    session.commit()
    session.refresh(item)

    assert item.created_at == created
    assert item.updated_at > first_updated


def test_primary_key_naming_convention():
    assert SampleItem.__table__.primary_key.name == "pk_sample_items"