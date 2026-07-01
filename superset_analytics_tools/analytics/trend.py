from typing import Any

import numpy as np
import pandas as pd
import ruptures as rpt

from ..schemas import analytics_schemas


def detect_timeseries_anomalies_auto(
    data: list[dict[str, Any]],
    time_col: str,
    metric_col: str,
    rolling_window: int = 12,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    max_anomalies: int = 100,
) -> (
    analytics_schemas.TimeseriesAnomalyResult
    | analytics_schemas.AnalyticsError
):
    df = pd.DataFrame(data)

    if df.empty:
        return analytics_schemas.AnalyticsError(error="Input data is empty")

    if time_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"time_col '{time_col}' not found"
        )

    if metric_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"metric_col '{metric_col}' not found"
        )

    df[time_col] = pd.to_datetime(df[time_col], errors="coerce", unit='ms')
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")

    df = df.dropna(subset=[time_col, metric_col])
    df = df.sort_values(time_col).reset_index(drop=True)
     
    min_row_require = 20
    if len(df) < min_row_require:
        return analytics_schemas.AnalyticsError(
            error=f"Not enough valid rows for time-series anomaly detection, total row data has {len(df)}, min row require {min_row_require}",
        )

    values = df[metric_col]

    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1

    iqr_lower = q1 - iqr_multiplier * iqr
    iqr_upper = q3 + iqr_multiplier * iqr

    df["iqr_anomaly"] = (values < iqr_lower) | (values > iqr_upper)

    min_periods = max(3, rolling_window // 2)
    history = values.shift(1)

    df["rolling_mean"] = history.rolling(
        window=rolling_window,
        min_periods=min_periods,
    ).mean()

    df["rolling_std"] = history.rolling(
        window=rolling_window,
        min_periods=min_periods,
    ).std()

    df["rolling_z_score"] = (
        (values - df["rolling_mean"])
        / df["rolling_std"].replace(0, np.nan)
    )

    df["rolling_z_anomaly"] = df["rolling_z_score"].abs() > z_threshold

    change_points: list[analytics_schemas.ChangePoint] = []
    pen = float(max(10, np.log(len(values)) * 3))

    try:
        signal = values.to_numpy().reshape(-1, 1)

        algo = rpt.Pelt(model="l2").fit(signal)
        points = algo.predict(pen=pen)

        actual_points = [p for p in points[:-1] if p < len(df)]

        window = min(20, max(5, len(df) // 10))

        for cp in actual_points:
            before = values.iloc[max(0, cp - window):cp]
            after = values.iloc[cp:min(len(df), cp + window)]

            if before.empty or after.empty:
                continue

            before_mean = before.mean()
            after_mean = after.mean()
            delta = after_mean - before_mean

            delta_pct = None
            if before_mean != 0:
                delta_pct = (delta / abs(before_mean)) * 100

            change_points.append(analytics_schemas.ChangePoint(
                index=int(cp),
                timestamp=df.iloc[cp][time_col].isoformat(),
                metric_col=metric_col,
                before_mean=float(before_mean),
                after_mean=float(after_mean),
                delta=float(delta),
                delta_pct=None if delta_pct is None else float(delta_pct),
                direction="increase" if delta > 0 else "decrease",
            ))

    except Exception as e:
        change_points_error = str(e)
    else:
        change_points_error = None

    anomaly_rows = df[
        df["iqr_anomaly"]
        | df["rolling_z_anomaly"]
    ]

    anomalies: list[analytics_schemas.TimeseriesAnomaly] = []
    median_value = values.median()

    for _, row in anomaly_rows.iterrows():
        methods = []

        if row["iqr_anomaly"]:
            methods.append("iqr")

        if row["rolling_z_anomaly"]:
            methods.append("rolling_zscore")

        reference_value = row["rolling_mean"]

        if pd.isna(reference_value):
            reference_value = median_value

        direction = "spike" if row[metric_col] > reference_value else "drop"

        anomalies.append(analytics_schemas.TimeseriesAnomaly(
            timestamp=row[time_col].isoformat(),
            metric_col=metric_col,
            value=float(row[metric_col]),
            direction=direction,
            methods=methods,
            rolling_mean=None if pd.isna(row["rolling_mean"]) else float(row["rolling_mean"]),
            rolling_z_score=None if pd.isna(row["rolling_z_score"]) else float(row["rolling_z_score"]),
        ))

    return analytics_schemas.TimeseriesAnomalyResult(
        time_col=time_col,
        metric_col=metric_col,
        row_count=len(df),
        time_start=df[time_col].min().isoformat(),
        time_end=df[time_col].max().isoformat(),
        methods_run=[
            "iqr",
            "rolling_zscore",
            "change_point_pelt_l2",
        ],
        thresholds=analytics_schemas.TimeseriesThresholds(
            iqr_lower=float(iqr_lower),
            iqr_upper=float(iqr_upper),
            z_threshold=z_threshold,
            rolling_window=rolling_window,
            change_point_penalty=pen,
        ),
        point_anomaly_count=len(anomalies),
        anomalies=anomalies[:max_anomalies],
        change_point_count=len(change_points),
        change_points=change_points,
        change_points_error=change_points_error,
    )
