from typing import Any

from pydantic import BaseModel, Field


class CanonicalDatasetColumn(BaseModel):
    source_id: str | None = None
    name: str
    description: str | None = None
    data_type: str
    is_temporal: bool = False
    expression: str | None = None


class CanonicalMetric(BaseModel):
    source_id: str | None = None
    name: str
    description: str | None = None
    expression: str


class CanonicalDataset(BaseModel):
    source_id: str
    name: str
    description: str | None = None
    extra: dict[str, Any] | None = None
    columns: list[CanonicalDatasetColumn] = Field(default_factory=list)
    metrics: list[CanonicalMetric] = Field(default_factory=list)
