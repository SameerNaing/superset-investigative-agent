from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from ..schemas import analytics_schemas


def detect_relationship_anomalies(
    data: list[dict[str, Any]],
    x_col: str,
    y_col: str,
    residual_z_threshold: float = 3.0,
    max_anomalies: int = 100,
) -> (
    analytics_schemas.RelationalAnomalyResult
    | analytics_schemas.AnalyticsError
):
    df = pd.DataFrame(data)

    if df.empty:
        return analytics_schemas.AnalyticsError(error="Input data is empty")

    if x_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"x_col '{x_col}' not found"
        )

    if y_col not in df.columns:
        return analytics_schemas.AnalyticsError(
            error=f"y_col '{y_col}' not found"
        )

    df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")

    df = df.dropna(subset=[x_col, y_col]).reset_index(drop=True)

    min_require_rows = 20
    if len(df) < min_require_rows:
        return analytics_schemas.AnalyticsError(
            error=f"Not enough valid rows for relationship analysis. The data has {len(df)} rows, but {min_require_rows} are required.",
        )

    zero_var_cols = {
    "x_col": x_col,
    "y_col": y_col,
    }

    zero_var = [f"'{name}' ({col})" for name, col in zero_var_cols.items() if df[col].std() == 0]

    if zero_var:
        return analytics_schemas.AnalyticsError(
            error=f"{'and'.join(zero_var)} {'have' if len(zero_var) > 1 else 'has'} zero variance"
        )

    correlation = float(df[x_col].corr(df[y_col]))

    abs_corr = abs(correlation)

    if abs_corr >= 0.7:
        strength = "strong"
    elif abs_corr >= 0.4:
        strength = "moderate"
    elif abs_corr >= 0.2:
        strength = "weak"
    else:
        strength = "very_weak"

    direction = "positive" if correlation > 0 else "negative"

    X = df[[x_col]]
    y = df[y_col]

    model = LinearRegression()
    model.fit(X, y)

    df["predicted_y"] = model.predict(X)
    df["residual"] = df[y_col] - df["predicted_y"]

    residual_std = df["residual"].std()

    if pd.isna(residual_std) or residual_std == 0:
        df["residual_z_score"] = np.nan
        df["relationship_anomaly"] = False
    else:
        df["residual_z_score"] = df["residual"] / residual_std
        df["relationship_anomaly"] = (
            df["residual_z_score"].abs() > residual_z_threshold
        )

    anomaly_rows = df[df["relationship_anomaly"]]

    anomalies: list[analytics_schemas.RelationshipAnomaly] = []

    for idx, row in anomaly_rows.iterrows():
        anomalies.append(analytics_schemas.RelationshipAnomaly(
            index=int(idx),
            predicted_y=float(row["predicted_y"]),
            residual=float(row["residual"]),
            residual_z_score=float(row["residual_z_score"]),
            direction=(
                "above_expected"
                if row["residual"] > 0
                else "below_expected"
            ),
            methods=["linear_regression_residual_zscore"],
            **{x_col: float(row[x_col]), y_col: float(row[y_col])},
        ))

    return analytics_schemas.RelationalAnomalyResult(
        x_col=x_col,
        y_col=y_col,
        row_count=len(df),
        methods_run=[
            "pearson_correlation",
            "linear_regression_residual_outliers",
        ],
        correlation=correlation,
        relationship=analytics_schemas.RelationshipInfo(
            strength=strength,
            direction=direction,
            slope=float(model.coef_[0]),
            intercept=float(model.intercept_),
            r_squared=float(model.score(X, y)),
        ),
        thresholds=analytics_schemas.RelationalThresholds(
            residual_z_threshold=residual_z_threshold,
        ),
        anomaly_count=len(anomalies),
        anomalies=anomalies[:max_anomalies],
    )
