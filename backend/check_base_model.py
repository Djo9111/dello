from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import engine
from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SampleItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sample_items"

    name: Mapped[str] = mapped_column(String(50))


Base.metadata.create_all(engine, tables=[SampleItem.__table__])

try:
    with Session(engine) as session:
        item = SampleItem(name="essai")
        session.add(item)
        session.commit()
        session.refresh(item)

        print("---- RESULTAT ----")
        print("id         :", item.id, type(item.id).__name__)
        print("created_at :", item.created_at)
        print("fuseau     :", item.created_at.tzinfo)
        print("contrainte :", SampleItem.__table__.primary_key.name)
finally:
    Base.metadata.drop_all(engine, tables=[SampleItem.__table__])