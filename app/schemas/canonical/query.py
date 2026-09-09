from typing import Any

from pydantic import BaseModel, Field

from app.db.models.query import FilterClause, FilterOperator, FilterType


class CanonicalQueryColumn(BaseModel):
    """Reference to a dataset column used in SELECT / GROUP BY."""

    column_name: str
    time_grain: str | None = None
    # Present for Superset adhoc columns (sqlExpression + label).
    expression: str | None = None


class CanonicalQueryMetric(BaseModel):
    """Reference to a dataset/adhoc metric used in SELECT."""

    metric_name: str
    expression: str | None = None
    source_id: str | None = None


class CanonicalQueryFilter(BaseModel):
    clause: FilterClause
    filter_type: FilterType
    operator: FilterOperator | None = None
    value: Any | None = None
    expression: str | None = None
    column_name: str | None = None
    metric_name: str | None = None


class CanonicalQueryOrder(BaseModel):
    column_name: str | None = None
    metric_name: str | None = None
    # Present when orderby target is an adhoc metric/column object.
    expression: str | None = None
    asc: bool = False
    position: int


class CanonicalQuery(BaseModel):
    position: int = 0
    row_limit: int | None = None
    columns: list[CanonicalQueryColumn] = Field(default_factory=list)
    metrics: list[CanonicalQueryMetric] = Field(default_factory=list)
    filters: list[CanonicalQueryFilter] = Field(default_factory=list)
    orders: list[CanonicalQueryOrder] = Field(default_factory=list)
