from typing import Any, Literal

from pydantic import BaseModel, Field

from ..constants.consts import ChartMark

class ChartSeries(BaseModel):
    data_key: str = Field(
        description="Column name in the data array."
    )
    viz_type: ChartMark = Field(
        description="Visualization type for this series."
    )
    is_secondary: bool = Field(
        default=False,
        description="Whether this series uses the secondary Y axis."
    )
    stack_id: str | None = Field(
        default=None,
        description="Stack identifier for stacked bar charts. None if not stacked."
    )


class CartesianChart(BaseModel):
    title: str = Field(
        description="Chart title."
    )
    
    interpretation: str = Field(
        description="Interpretation of the chart."
    )
    
    chart_type: Literal["cartesian"] = Field(
        default="cartesian",
        description="Chart family."
    )
    
    x_key: str = Field(
        description="Column name used for the X axis."
    )
    
    x_title: str | None = Field(
        default=None,
        description="Title of the X axis.",
    )
    y_title: str | None = Field(
        default=None,
        description="Title of the Y axis.",
    )

    y_secondary_title: str | None = Field(
        default=None,
        description="Title of the secondary Y axis.",
    )
    
    data: list[dict[str, Any]] = Field(
        description="Chart data. Each item is a row containing the x-axis value and series values."
    )
    series: list[ChartSeries] = Field(
        description="Series definitions for rendering."
    )
    is_secondary_enabled: bool = Field(
        default=False,
        description="Whether the chart contains a secondary Y axis."
    )