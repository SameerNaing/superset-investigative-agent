from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.superset_schemas import Analytics


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