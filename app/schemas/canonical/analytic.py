from typing import Any

from pydantic import BaseModel, Field

from app.schemas.canonical.query import CanonicalQuery
from app.schemas.canonical.visualization import CanonicalVisualization


class CanonicalAnalytic(BaseModel):
    source_id: str
    name: str
    description: str | None = None
    dataset_source_id: str
    queries: list[CanonicalQuery] = Field(default_factory=list)
    visualization: CanonicalVisualization | None = None
    unsupported: list[dict[str, Any]] = Field(default_factory=list)
