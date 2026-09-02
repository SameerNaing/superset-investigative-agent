from typing import Any

import pandas as pd

from ..schemas import analytics_schemas


def detect_cross_section_anomalies(
    data: list[dict[str, Any]],
    category_col: str,
    metric_col: str,
    iqr_multiplier: float = 1.5,
    max_anomalies: int = 100,
) -> (
    analytics_schemas.CrossSectionAnomalyResult
    | analytics_schemas.AnalyticsError
):
    df = pd.DataFrame(data)

    if df.empty:
        return analytics_schemas.AnalyticsError(error="Input data is empty")

    if category_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"category_col '{category_col}' not found"
        )

    if metric_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"metric_col '{metric_col}' not found"
        )

    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")

    df = df.dropna(subset=[category_col, metric_col])
    
    min_row_require = 15
    if len(df) < min_row_require:
        return analytics_schemas.AnalyticsError(
            error=f"Not enough valid rows. The data has total rows {len(df)}, min row require {min_row_require}",
        )

    grouped = (
        df.groupby(category_col, dropna=False)[metric_col]
        .mean()
        .reset_index()
    )

    values = grouped[metric_col]

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    iqr_lower = q1 - (iqr_multiplier * iqr)
    iqr_upper = q3 + (iqr_multiplier * iqr)

    grouped["iqr_anomaly"] = (
        (values < iqr_lower)
        | (values > iqr_upper)
    )

    median_value = values.median()

    if median_value == 0:
        grouped["deviation_pct"] = None
    else:
        grouped["deviation_pct"] = (
            (values - median_value)
            / abs(median_value)
        ) * 100

    anomaly_rows = grouped[grouped["iqr_anomaly"]]

    anomalies: list[analytics_schemas.CrossSectionAnomaly] = []

    for _, row in anomaly_rows.iterrows():
        deviation_pct = row["deviation_pct"]

        anomalies.append(analytics_schemas.CrossSectionAnomaly(
            category=str(row[category_col]),
            value=float(row[metric_col]),
            direction=(
                "high"
                if row[metric_col] > median_value
                else "low"
            ),
            peer_median=float(median_value),
            deviation_pct=(
                None
                if pd.isna(deviation_pct)
                else float(deviation_pct)
            ),
            methods=["iqr"],
        ))

    return analytics_schemas.CrossSectionAnomalyResult(
        category_col=category_col,
        metric_col=metric_col,
        category_count=len(grouped),
        methods_run=[
            "iqr",
            "median_deviation_pct",
        ],
        thresholds=analytics_schemas.CrossSectionThresholds(
            iqr_lower=float(iqr_lower),
            iqr_upper=float(iqr_upper),
        ),
        peer_median=float(median_value),
        anomaly_count=len(anomalies),
        anomalies=anomalies[:max_anomalies],
    )
