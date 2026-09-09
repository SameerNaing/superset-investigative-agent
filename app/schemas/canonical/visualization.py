from typing import Any

from pydantic import BaseModel

from app.db.models.visualization import VizType


class CanonicalVisualization(BaseModel):
    source_id: str | None = None
    name: str
    description: str | None = None
    viz_type: VizType
    options: dict[str, Any] | None = None
