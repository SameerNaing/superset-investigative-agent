import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.dataset import Dataset
    from app.db.models.query import Query
    from app.db.models.visualization import Visualization


class Analytic(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "analytic"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_id",
            name="uq_analytic_dataset_source_id",
        ),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset.id"),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    dataset: Mapped["Dataset"] = relationship(back_populates="analytics")
    queries: Mapped[list["Query"]] = relationship(
        back_populates="analytic",
        order_by="Query.position",
    )
    visualizations: Mapped[list["Visualization"]] = relationship(
        back_populates="analytic",
    )
