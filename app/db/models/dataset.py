import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.analytic import Analytic
    from app.db.models.data_source import DataSource
    from app.db.models.query import QueryColumn, QueryFilter, QueryMetric, QueryOrder


class Dataset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dataset"
    __table_args__ = (
        UniqueConstraint(
            "data_source_id",
            "source_id",
            name="uq_dataset_data_source_source_id",
        ),
    )

    data_source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("data_source.id"),
        nullable=False,
    )
    source_id: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    data_source: Mapped["DataSource"] = relationship(back_populates="datasets")
    columns: Mapped[list["DatasetColumn"]] = relationship(back_populates="dataset")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="dataset")
    analytics: Mapped[list["Analytic"]] = relationship(back_populates="dataset")


class DatasetColumn(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dataset_column"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_id",
            name="uq_dataset_column_dataset_source_id",
        ),
        # Name alone is not unique: chart adhoc columns may reuse a label with
        # a different SQL expression than a dataset-registered column.
        UniqueConstraint(
            "dataset_id",
            "name",
            "expression",
            name="uq_dataset_column_dataset_name_expression",
            postgresql_nulls_not_distinct=True,
        ),
    )

    source_id: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_type: Mapped[str] = mapped_column(String, nullable=False)
    is_temporal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expression: Mapped[str | None] = mapped_column(Text)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset.id"),
        nullable=False,
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="columns")
    query_columns: Mapped[list["QueryColumn"]] = relationship(
        back_populates="column",
    )
    query_filters: Mapped[list["QueryFilter"]] = relationship(
        back_populates="column",
    )
    query_orders: Mapped[list["QueryOrder"]] = relationship(
        back_populates="column",
    )


class Metric(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "metric"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_id",
            name="uq_metric_dataset_source_id",
        ),
        UniqueConstraint(
            "dataset_id",
            "name",
            "expression",
            name="uq_metric_dataset_name_expression",
        ),
    )

    source_id: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset.id"),
        nullable=False,
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="metrics")
    query_metrics: Mapped[list["QueryMetric"]] = relationship(
        back_populates="metric",
    )
    query_filters: Mapped[list["QueryFilter"]] = relationship(
        back_populates="metric",
    )
    query_orders: Mapped[list["QueryOrder"]] = relationship(
        back_populates="metric",
    )
