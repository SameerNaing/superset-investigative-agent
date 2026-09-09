import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.analytic import Analytic
    from app.db.models.dataset import DatasetColumn, Metric


class FilterClause(str, enum.Enum):
    WHERE = "where"
    HAVING = "having"


class FilterOperator(str, enum.Enum):
    EQ = "=="
    NEQ = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    ILIKE = "ILIKE"
    NOT_ILIKE = "NOT ILIKE"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    IN = "IN"
    NOT_IN = "NOT IN"
    TEMPORAL_RANGE = "temporal range"


class FilterType(str, enum.Enum):
    STRUCTURED = "structured"
    EXPRESSION = "expression"


class Query(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "query"
    __table_args__ = (UniqueConstraint("analytic_id", "position"),)

    analytic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analytic.id"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_limit: Mapped[int | None] = mapped_column(Integer)

    analytic: Mapped["Analytic"] = relationship(back_populates="queries")
    columns: Mapped[list["QueryColumn"]] = relationship(back_populates="query")
    metrics: Mapped[list["QueryMetric"]] = relationship(back_populates="query")
    filters: Mapped[list["QueryFilter"]] = relationship(back_populates="query")
    orders: Mapped[list["QueryOrder"]] = relationship(
        back_populates="query",
        order_by="QueryOrder.position",
    )


class QueryColumn(Base):
    __tablename__ = "query_column"

    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("query.id"),
        primary_key=True,
    )
    column_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_column.id"),
        primary_key=True,
    )
    time_grain: Mapped[str | None] = mapped_column(String)

    query: Mapped["Query"] = relationship(back_populates="columns")
    column: Mapped["DatasetColumn"] = relationship(back_populates="query_columns")


class QueryMetric(Base):
    __tablename__ = "query_metric"

    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("query.id"),
        primary_key=True,
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("metric.id"),
        primary_key=True,
    )

    query: Mapped["Query"] = relationship(back_populates="metrics")
    metric: Mapped["Metric"] = relationship(back_populates="query_metrics")


class QueryFilter(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "query_filter"

    clause: Mapped[FilterClause] = mapped_column(
        Enum(FilterClause, name="filter_clause", native_enum=True),
        nullable=False,
    )
    filter_type: Mapped[FilterType | None] = mapped_column(
        "type",
        Enum(FilterType, name="filter_type", native_enum=True),
    )
    operator: Mapped[FilterOperator | None] = mapped_column(
        Enum(FilterOperator, name="filter_operator", native_enum=True),
    )
    value: Mapped[Any | None] = mapped_column(JSONB)
    expression: Mapped[str | None] = mapped_column(Text)
    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("query.id"),
        nullable=False,
    )
    column_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_column.id"),
    )
    metric_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("metric.id"),
    )

    query: Mapped["Query"] = relationship(back_populates="filters")
    column: Mapped["DatasetColumn | None"] = relationship(
        back_populates="query_filters"
    )
    metric: Mapped["Metric | None"] = relationship(back_populates="query_filters")


class QueryOrder(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "query_order"
    __table_args__ = (UniqueConstraint("query_id", "position"),)

    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("query.id"),
        nullable=False,
    )
    column_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_column.id"),
    )
    metric_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("metric.id"),
    )
    asc: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    query: Mapped["Query"] = relationship(back_populates="orders")
    column: Mapped["DatasetColumn | None"] = relationship(back_populates="query_orders")
    metric: Mapped["Metric | None"] = relationship(back_populates="query_orders")
