import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.dataset import Dataset


class Provider(str, enum.Enum):
    SUPERSET = "superset"
    RAW_DB = "raw_db"


class DataSource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "data_source"

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[Provider] = mapped_column(
        Enum(Provider, name="provider", native_enum=True),
        nullable=False,
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="data_source",
    )
