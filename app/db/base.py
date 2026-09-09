import uuid

from sqlalchemy import MetaData, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    metadata = MetaData(schema="bi")


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


@event.listens_for(Base, "init", propagate=True)
def _assign_uuid_pk_on_init(target: object, args: tuple, kwargs: dict) -> None:
    """Assign UUID PKs at construction so FKs can reference them before flush.

    SQLAlchemy column ``default=uuid.uuid4`` only runs at INSERT time, so
    ``new_obj.id`` is otherwise ``None`` when building related rows in the
    same unit of work (e.g. DatasetColumn → QueryColumn).
    """
    mapper = getattr(type(target), "__mapper__", None)
    if mapper is None or "id" not in mapper.columns:
        return
    if "id" not in kwargs:
        kwargs["id"] = uuid.uuid4()
