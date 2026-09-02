import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.analytic import Analytic


class VizType(str, enum.Enum):
    LINE = "line"
    BAR = "bar"
    BOX = "box"
    TABLE = "table"
    PIVOT_TABLE = "pivot_table"
    MIXED_CHART = "mixed_chart"
    SANKEY_CHART = "sankey_chart"
    AREA_CHART = "area_chart"
    HISTOGRAM = "histogram"


class Visualization(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "visualization"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(String)
    analytic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analytic.id"),
        nullable=False,
    )
    viz_type: Mapped[VizType] = mapped_column(
        "type",
        Enum(VizType, name="viz_type", native_enum=True),
        nullable=False,
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    options: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    analytic: Mapped["Analytic"] = relationship(back_populates="visualizations")
