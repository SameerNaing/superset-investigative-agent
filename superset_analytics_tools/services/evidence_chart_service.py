import json
from uuid import uuid4

import pandas as pd

from ..client.superset_client import get_chart_info
from ..constants.consts import ChartMark
from ..constants.superset_consts import VizType
from ..environments import CHARTS_DIR
from ..schemas.chart_viz_schemas import CartesianChart, ChartSeries


class EvidenceChartService:
    def get(
        self,
        chart_id: int | str,
        interpretation: str,
        data: dict,
    ) -> dict:
        chart_info = get_chart_info(chart_id)
        params = chart_info.get("params", {})
        if isinstance(params, str):
            params = json.loads(params)

        title = chart_info.get("slice_name", "")
        viz_type = chart_info.get("viz_type", "")
        x_key = params.get("x_axis")
        x_title = params.get("x_axis_title")
        y_title = params.get("y_axis_title")
        stack_b = params.get("stackB")
        stack = params.get("stack")
        y_secondary_title = params.get("yAxisTitleSecondary")
        is_secondary_enabled = params.get("yAxisIndexB", 0) > 0

        data_1 = data.get("data_1") or []
        data_2 = data.get("data_2") or []

        series = self._build_series(
            viz_type=viz_type,
            params=params,
            x_key=x_key,
            data_1=data_1,
            data_2=data_2,
            stack=stack,
            stack_b=stack_b,
            is_secondary_enabled=is_secondary_enabled,
        )
        chart_data = self._build_chart_data(data_1, data_2, x_key)

        chart = CartesianChart(
            title=title,
            interpretation=interpretation,
            x_key=x_key,
            x_title=x_title,
            y_title=y_title,
            y_secondary_title=y_secondary_title,
            data=chart_data,
            series=series,
            is_secondary_enabled=is_secondary_enabled,
        )

        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        chart_file_id = str(uuid4())
        file_path = CHARTS_DIR / f"{chart_file_id}.json"
        file_path.write_text(
            json.dumps(chart.model_dump(), indent=2),
            encoding="utf-8",
        )

        return {
            "viz_id": chart_file_id,
            "interpretation": interpretation,
        }

    def _build_series(
        self,
        viz_type: str,
        params: dict,
        x_key: str,
        data_1: list[dict],
        data_2: list[dict],
        stack: bool,
        stack_b: bool,
        is_secondary_enabled: bool,
    ) -> list[ChartSeries]:
        series: list[ChartSeries] = []

        if viz_type == VizType.MIXED_TIMESERIES:
            if data_1:
                for col in data_1[0].keys():
                    if col == x_key:
                        continue
                    series.append(
                        ChartSeries(
                            data_key=col,
                            viz_type=params.get("seriesType", "line"),
                            is_secondary=False,
                            stack_id="stack" if stack else None,
                        )
                    )

            if data_2:
                for col in data_2[0].keys():
                    if col == x_key:
                        continue
                    series.append(
                        ChartSeries(
                            data_key=col,
                            viz_type=params.get("seriesTypeB", "line"),
                            is_secondary=is_secondary_enabled,
                            stack_id="stackB" if stack_b else None,
                        )
                    )
            return series

        viz_map = {
            VizType.LINE: ChartMark.LINE,
            VizType.SMOOTH_LINE: ChartMark.LINE,
            VizType.BAR: ChartMark.BAR,
            VizType.SCATTER: ChartMark.SCATTER,
        }

        if viz_type not in viz_map:
            raise ValueError(f"Unsupported chart viz_type for evidence chart: {viz_type}")

        stack_id = "stack" if params.get("stack") == "Stack" else None

        if not data_1:
            return series

        for col in data_1[0].keys():
            if col == x_key:
                continue
            series.append(
                ChartSeries(
                    data_key=col,
                    viz_type=viz_map[viz_type],
                    is_secondary=False,
                    stack_id=stack_id,
                )
            )

        return series

    def _format_x_axis_if_timestamp(self, df: pd.DataFrame, x_key: str) -> None:
        col = df[x_key]
        if pd.api.types.is_datetime64_any_dtype(col):
            df[x_key] = col.dt.strftime("%d-%m-%y %H:%M")
            return

        numeric = pd.to_numeric(col, errors="coerce")
        if numeric.notna().all() and len(numeric) > 0:
            df[x_key] = pd.to_datetime(numeric, unit="ms").dt.strftime(
                "%d-%m-%y %H:%M"
            )

    def _build_chart_data(
        self,
        data_1: list[dict],
        data_2: list[dict],
        x_key: str,
    ) -> list[dict]:
        if not data_1 and not data_2:
            return []

        if data_1 and data_2:
            df = pd.DataFrame(data_1).merge(
                pd.DataFrame(data_2), on=x_key, how="outer"
            )
        elif data_1:
            df = pd.DataFrame(data_1)
        else:
            df = pd.DataFrame(data_2)

        df = df.sort_values(x_key)
        self._format_x_axis_if_timestamp(df, x_key)
        df = df.where(pd.notnull(df), None)

        return json.loads(df.to_json(orient="records"))

