from typing import Literal, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field


from ..schemas.superset_schemas import Analytics, AppliedFilter
from ..constants.consts import QueryType

class AnalyticsError(BaseModel):
    error: str
    
# ---------------------------------------------------------------------------
# Timeseries
# ---------------------------------------------------------------------------
class TimeseriesAnomaly(BaseModel):
    timestamp: str
    metric_col: str
    value: float
    direction: Literal["spike", "drop"]
    methods: list[str]
    rolling_mean: float | None = None
    rolling_z_score: float | None = None


class ChangePoint(BaseModel):
    index: int
    timestamp: str
    metric_col: str
    before_mean: float
    after_mean: float
    delta: float
    delta_pct: float | None = None
    direction: Literal["increase", "decrease"]


class TimeseriesThresholds(BaseModel):
    iqr_lower: float
    iqr_upper: float
    z_threshold: float
    rolling_window: int
    change_point_penalty: float


class TimeseriesAnomalyResult(BaseModel):
    analysis_type: Literal[Analytics.TIME_SERIES] = Analytics.TIME_SERIES
    time_col: str
    metric_col: str
    row_count: int
    time_start: str
    time_end: str
    methods_run: list[str]
    thresholds: TimeseriesThresholds
    point_anomaly_count: int
    anomalies: list[TimeseriesAnomaly]
    change_point_count: int
    change_points: list[ChangePoint]
    change_points_error: str | None = None


# ---------------------------------------------------------------------------
# Cross Section
# ---------------------------------------------------------------------------
class CrossSectionAnomaly(BaseModel):
    category: str
    value: float
    direction: Literal["high", "low"]
    peer_median: float
    deviation_pct: float | None = None
    methods: list[str]


class CrossSectionThresholds(BaseModel):
    iqr_lower: float
    iqr_upper: float


class CrossSectionAnomalyResult(BaseModel):
    analysis_type: Literal[Analytics.CROSS_SECTION] = Analytics.CROSS_SECTION
    category_col: str
    metric_col: str
    category_count: int
    methods_run: list[str]
    thresholds: CrossSectionThresholds
    peer_median: float
    anomaly_count: int
    anomalies: list[CrossSectionAnomaly]


# ---------------------------------------------------------------------------
# Relational
# ---------------------------------------------------------------------------
class RelationshipAnomaly(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int
    predicted_y: float
    residual: float
    residual_z_score: float
    direction: Literal["above_expected", "below_expected"]
    methods: list[str]


class RelationshipInfo(BaseModel):
    strength: Literal["strong", "moderate", "weak", "very_weak"]
    direction: Literal["positive", "negative"]
    slope: float
    intercept: float
    r_squared: float


class RelationalThresholds(BaseModel):
    residual_z_threshold: float


class RelationalAnomalyResult(BaseModel):
    analysis_type: Literal[Analytics.RELATIONAL] = Analytics.RELATIONAL
    x_col: str
    y_col: str
    row_count: int
    methods_run: list[str]
    correlation: float
    relationship: RelationshipInfo
    thresholds: RelationalThresholds
    anomaly_count: int
    anomalies: list[RelationshipAnomaly]


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
class SummaryResult(BaseModel):
    summary: str
    key_observations: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Data Source
# ---------------------------------------------------------------------------
class ChartAnalyticsSource(BaseModel):
    source_type: Literal["chart"] = Field(
        description=(
            "Load data from an existing Superset chart. "
            "Use this source when analyzing chart data."
        )
    )

    chart_id: int = Field(
        description=(
            "The unique Superset chart ID containing the data to analyze."
        )
    )

    filter: list[AppliedFilter] = Field(
        default_factory=list,
        description=(
            "Filters to apply before retrieving the chart data. "
            "Use an empty list when no additional filters are required."
        )
    )

    query_type: QueryType | None = Field(
        default=None,
        description=(
            "Query selection for Mixed charts containing multiple queries. "
            "Leave null for charts with a single query."
        )
    )

    time_grain: str | None = Field(
        default=None,
        description=(
            "Optional time aggregation to apply when retrieving chart data, "
            "such as P1D, PTH, etc. the superset time grain codes. "
            "Leave null to use the chart's existing time grain."
        )
    )


class SQLExecutionAnalyticsSource(BaseModel):
    source_type: Literal["sql_execution"] = Field(
        description=(
            "Load data from a previously executed SQL query stored for "
            "analytics."
        )
    )

    execution_id: str = Field(
        description=(
            "The execution ID returned by the analytics SQL execution tool. "
            "The analytics tool will load the stored SQL result associated "
            "with this ID."
        )
    )


AnalyticsDataSource = Annotated[
    Union[
        ChartAnalyticsSource,
        SQLExecutionAnalyticsSource,
    ],
    Field(
        discriminator="source_type",
        description=(
            "Reference describing where the analytics data should be loaded "
            "from. Select either a Superset chart or a previously stored SQL "
            "execution result."
        ),
    ),
]