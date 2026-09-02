from typing import Any

from ..analytics import (
    detect_cross_section_anomalies,
    detect_relationship_anomalies,
    detect_timeseries_anomalies_auto,
)
from ..schemas import analytics_schemas


class AnomalyService:
    def detect_timeseries(
        self,
        data: list[dict[str, Any]],
        time_col: str,
        metric_col: str,
        **kwargs,
    ) -> (
        analytics_schemas.TimeseriesAnomalyResult
        | analytics_schemas.AnalyticsError
    ):
        return detect_timeseries_anomalies_auto(
            data, time_col, metric_col, **kwargs
        )

    def detect_cross_section(
        self,
        data: list[dict[str, Any]],
        category_col: str,
        metric_col: str,
        **kwargs,
    ) -> (
        analytics_schemas.CrossSectionAnomalyResult
        | analytics_schemas.AnalyticsError
    ):
        return detect_cross_section_anomalies(
            data, category_col, metric_col, **kwargs
        )

    def detect_relationship(
        self,
        data: list[dict[str, Any]],
        x_col: str,
        y_col: str,
        **kwargs,
    ) -> (
        analytics_schemas.RelationalAnomalyResult
        | analytics_schemas.AnalyticsError
    ):
        return detect_relationship_anomalies(data, x_col, y_col, **kwargs)
