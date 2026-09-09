"""Convert Superset API payloads into provider-independent canonical schemas."""

from __future__ import annotations

import json
from typing import Any

from app.db.models.query import FilterClause, FilterOperator, FilterType
from app.db.models.visualization import VizType
from app.integrations.superset.time_grains import (
    TimeGrainCatalog,
    normalize_time_grain,
)
from app.schemas.canonical import (
    CanonicalAnalytic,
    CanonicalDataset,
    CanonicalDatasetColumn,
    CanonicalMetric,
    CanonicalQuery,
    CanonicalQueryColumn,
    CanonicalQueryFilter,
    CanonicalQueryMetric,
    CanonicalQueryOrder,
    CanonicalVisualization,
)

NO_TIME_RANGE = "No filter"

# Superset query filter `op` values -> canonical FilterOperator
_OPERATOR_MAP: dict[str, FilterOperator] = {
    "==": FilterOperator.EQ,
    "!=": FilterOperator.NEQ,
    ">": FilterOperator.GT,
    "<": FilterOperator.LT,
    ">=": FilterOperator.GTE,
    "<=": FilterOperator.LTE,
    "LIKE": FilterOperator.LIKE,
    "NOT LIKE": FilterOperator.NOT_LIKE,
    "ILIKE": FilterOperator.ILIKE,
    "NOT ILIKE": FilterOperator.NOT_ILIKE,
    "IS NULL": FilterOperator.IS_NULL,
    "IS NOT NULL": FilterOperator.IS_NOT_NULL,
    "IN": FilterOperator.IN,
    "NOT IN": FilterOperator.NOT_IN,
    "TEMPORAL_RANGE": FilterOperator.TEMPORAL_RANGE,
    "temporal range": FilterOperator.TEMPORAL_RANGE,
}

_VIZ_TYPE_MAP: dict[str, VizType] = {
    "echarts_timeseries_line": VizType.LINE,
    "echarts_timeseries": VizType.LINE,
    "echarts_timeseries_smooth": VizType.LINE,
    "echarts_timeseries_step": VizType.LINE,
    "echarts_timeseries_scatter": VizType.LINE,
    "echarts_timeseries_bar": VizType.BAR,
    "box_plot": VizType.BOX,
    "table": VizType.TABLE,
    "ag-grid-table": VizType.TABLE,
    "pivot_table_v2": VizType.PIVOT_TABLE,
    "mixed_timeseries": VizType.MIXED_CHART,
    "sankey_v2": VizType.SANKEY_CHART,
    "sankey": VizType.SANKEY_CHART,
    "echarts_area": VizType.AREA_CHART,
    "histogram_v2": VizType.HISTOGRAM,
    "histogram": VizType.HISTOGRAM,
}

# Superset Dataset editor ships unsaved calculated-column UI placeholders
# (see integration tests in datasource_tests.py).
_PLACEHOLDER_COLUMN_NAMES = frozenset({"<new column>"})
_PLACEHOLDER_COLUMN_EXPRESSIONS = frozenset({"<enter SQL expression here>"})


def _is_placeholder_dataset_column(source: dict[str, Any]) -> bool:
    name = (source.get("column_name") or "").strip()
    expression = (source.get("expression") or "").strip()
    if name in _PLACEHOLDER_COLUMN_NAMES:
        return True
    if expression in _PLACEHOLDER_COLUMN_EXPRESSIONS:
        return True
    return False


class SupersetAdapter:
    """Pure conversion from Superset structures to canonical schemas."""

    def to_dataset(self, source: dict[str, Any]) -> CanonicalDataset:
        dataset_id = source.get("id")
        if dataset_id is None:
            raise ValueError("Superset dataset payload missing id")

        schema = source.get("schema")
        table_name = source.get("table_name")
        sql = source.get("sql")
        kind = source.get("kind")
        database = source.get("database") or {}

        extra: dict[str, Any] = {
            "kind": kind,
            "schema": schema,
            "table_name": table_name,
            "sql": sql,
            "main_dttm_col": source.get("main_dttm_col"),
            "database_id": database.get("id"),
            "database_name": database.get("database_name"),
        }
        # Live engine catalog: builtins + TIME_GRAIN_ADDONS − TIME_GRAIN_DENYLIST.
        if "time_grain_sqla" in source:
            extra["time_grains"] = TimeGrainCatalog.from_time_grain_sqla(
                source.get("time_grain_sqla")
            ).to_records()

        columns = [
            self.to_dataset_column(col)
            for col in (source.get("columns") or [])
            if col.get("column_name") and not _is_placeholder_dataset_column(col)
        ]
        metrics = [
            self.to_metric(metric)
            for metric in (source.get("metrics") or [])
            if metric.get("metric_name") and metric.get("expression")
        ]

        return CanonicalDataset(
            source_id=str(dataset_id),
            name=source.get("table_name")
            or source.get("datasource_name")
            or source.get("name")
            or f"dataset_{dataset_id}",
            description=source.get("description"),
            extra={k: v for k, v in extra.items() if v is not None},
            columns=columns,
            metrics=metrics,
        )

    def to_dataset_column(self, source: dict[str, Any]) -> CanonicalDatasetColumn:
        expression = (source.get("expression") or "").strip() or None
        data_type = source.get("type") or source.get("type_generic") or "UNKNOWN"
        source_id = source.get("id")
        return CanonicalDatasetColumn(
            source_id=str(source_id) if source_id is not None else None,
            name=source["column_name"],
            description=source.get("description") or source.get("verbose_name"),
            data_type=str(data_type),
            is_temporal=bool(source.get("is_dttm")),
            expression=expression,
        )

    def to_metric(self, source: dict[str, Any]) -> CanonicalMetric:
        source_id = source.get("id")
        return CanonicalMetric(
            source_id=str(source_id) if source_id is not None else None,
            name=source.get("verbose_name") or source["metric_name"],
            description=source.get("description"),
            expression=source["expression"],
        )

    def to_adhoc_metric(self, source: str | dict[str, Any]) -> CanonicalMetric:
        if isinstance(source, str):
            return CanonicalMetric(
                source_id=None,
                name=source,
                description=None,
                expression=source,
            )

        expression_type = (source.get("expressionType") or "").upper()
        label = source.get("label") or source.get("metric_name") or "metric"

        if expression_type == "SIMPLE":
            column = source.get("column") or {}
            column_name = column.get("column_name") or column.get("columnName") or ""
            aggregate = source.get("aggregate") or "SUM"
            expression = f"{aggregate}({column_name})" if column_name else aggregate
        elif expression_type == "SQL":
            expression = source.get("sqlExpression") or label
        else:
            expression = (
                source.get("sqlExpression") or source.get("expression") or label
            )

        return CanonicalMetric(
            source_id=None,
            name=label,
            description=None,
            expression=expression,
        )

    def to_analytic(
        self,
        chart: dict[str, Any],
        *,
        dataset_source_id: str | None = None,
        time_grains: TimeGrainCatalog | None = None,
    ) -> CanonicalAnalytic:
        chart_id = chart.get("id")
        if chart_id is None:
            raise ValueError("Superset chart payload missing id")

        params = chart.get("params") or {}
        if isinstance(params, str):
            params = json.loads(params or "{}")

        query_context = chart.get("query_context") or {}
        if isinstance(query_context, str):
            query_context = json.loads(query_context or "{}")

        datasource_id = (
            dataset_source_id
            or str(chart.get("datasource_id") or "")
            or str((query_context.get("datasource") or {}).get("id") or "")
        )
        if not datasource_id:
            raise ValueError(f"Chart {chart_id} has no datasource_id")

        form_data = query_context.get("form_data") or params
        viz_type = (
            chart.get("viz_type")
            or form_data.get("viz_type")
            or params.get("viz_type")
            or "table"
        )

        raw_queries = list(query_context.get("queries") or [])
        if not raw_queries:
            # Fall back to constructing a single query-like object from form_data.
            raw_queries = [self._form_data_as_query(form_data)]

        adhoc_metrics_by_label = self._collect_adhoc_metrics(form_data)
        queries: list[CanonicalQuery] = []
        unsupported: list[dict[str, Any]] = []

        for index, raw_query in enumerate(raw_queries):
            query, notes = self.to_query(
                raw_query,
                position=index,
                form_data=form_data,
                adhoc_metrics_by_label=adhoc_metrics_by_label,
                time_grains=time_grains,
            )
            queries.append(query)
            unsupported.extend(notes)

        visualization = self.to_visualization(
            chart_id=chart_id,
            name=chart.get("slice_name") or f"chart_{chart_id}",
            description=chart.get("description"),
            viz_type=viz_type,
            form_data=form_data,
            query_count=len(queries),
        )

        return CanonicalAnalytic(
            source_id=str(chart_id),
            name=chart.get("slice_name") or f"chart_{chart_id}",
            description=chart.get("description"),
            dataset_source_id=str(datasource_id),
            queries=queries,
            visualization=visualization,
            unsupported=unsupported,
        )

    def to_query(
        self,
        source: dict[str, Any],
        *,
        position: int = 0,
        form_data: dict[str, Any] | None = None,
        adhoc_metrics_by_label: dict[str, CanonicalMetric] | None = None,
        time_grains: TimeGrainCatalog | None = None,
    ) -> tuple[CanonicalQuery, list[dict[str, Any]]]:
        form_data = form_data or {}
        adhoc_metrics_by_label = adhoc_metrics_by_label or {}
        unsupported: list[dict[str, Any]] = []

        columns = self._map_query_columns(source, time_grains=time_grains)
        metrics = self._map_query_metrics(source, adhoc_metrics_by_label)
        filters = self._map_query_filters(source, unsupported)
        orders = self._map_query_orders(source, unsupported)

        for field in (
            "series_limit",
            "series_limit_metric",
            "post_processing",
            "annotation_layers",
            "time_offsets",
            "time_shift",
        ):
            value = source.get(field)
            if value:
                unsupported.append(
                    {
                        "field": field,
                        "reason": (
                            "analytically meaningful but out of canonical v1 scope"
                        ),
                        "value": (value if field != "post_processing" else "<omitted>"),
                    }
                )

        return (
            CanonicalQuery(
                position=position,
                row_limit=source.get("row_limit"),
                columns=columns,
                metrics=metrics,
                filters=filters,
                orders=orders,
            ),
            unsupported,
        )

    def to_visualization(
        self,
        *,
        chart_id: int | str,
        name: str,
        description: str | None,
        viz_type: str,
        form_data: dict[str, Any],
        query_count: int,
    ) -> CanonicalVisualization:
        mapped = _VIZ_TYPE_MAP.get(viz_type, VizType.TABLE)
        options: dict[str, Any] = {
            "superset_viz_type": viz_type,
        }
        if viz_type not in _VIZ_TYPE_MAP:
            options["viz_type_fallback"] = True

        if viz_type == "mixed_timeseries" or query_count > 1:
            options["query_encodings"] = [
                {
                    "position": 0,
                    "series_type": form_data.get("seriesType"),
                    "y_axis_index": form_data.get("yAxisIndex", 0),
                    "stack": form_data.get("stack"),
                    "area": form_data.get("area"),
                },
                {
                    "position": 1,
                    "series_type": form_data.get("seriesTypeB"),
                    "y_axis_index": form_data.get("yAxisIndexB", 1),
                    "stack": form_data.get("stackB"),
                    "area": form_data.get("areaB"),
                },
            ]
            mapped = VizType.MIXED_CHART

        return CanonicalVisualization(
            source_id=str(chart_id),
            name=name,
            description=description,
            viz_type=mapped,
            options=options,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _form_data_as_query(self, form_data: dict[str, Any]) -> dict[str, Any]:
        columns: list[Any] = []
        x_axis = form_data.get("x_axis")
        if x_axis:
            columns.append(x_axis)
        columns.extend(form_data.get("groupby") or [])
        if form_data.get("columns"):
            columns.extend(form_data.get("columns") or [])

        metrics = form_data.get("metrics")
        if metrics is None and form_data.get("metric") is not None:
            metrics = [form_data.get("metric")]

        filters = []
        for adhoc in form_data.get("adhoc_filters") or []:
            mapped = self._adhoc_filter_to_query_filter(adhoc)
            if mapped is not None:
                filters.append(mapped)

        extras: dict[str, Any] = {}
        if form_data.get("time_grain_sqla"):
            extras["time_grain_sqla"] = form_data["time_grain_sqla"]

        return {
            "columns": columns,
            "metrics": metrics or [],
            "filters": filters,
            "time_range": form_data.get("time_range"),
            "granularity": form_data.get("granularity_sqla")
            or form_data.get("granularity"),
            "extras": extras,
            "orderby": form_data.get("orderby"),
            "row_limit": form_data.get("row_limit"),
        }

    def _collect_adhoc_metrics(
        self,
        form_data: dict[str, Any],
    ) -> dict[str, CanonicalMetric]:
        collected: dict[str, CanonicalMetric] = {}
        for key in ("metrics", "metrics_b", "metric", "metric_b"):
            value = form_data.get(key)
            if value is None:
                continue
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict):
                    metric = self.to_adhoc_metric(item)
                    collected[metric.name] = metric
        return collected

    def _map_query_columns(
        self,
        source: dict[str, Any],
        *,
        time_grains: TimeGrainCatalog | None = None,
    ) -> list[CanonicalQueryColumn]:
        raw_columns = list(source.get("columns") or [])
        # Legacy groupby may still appear on older query_context payloads.
        for group in source.get("groupby") or []:
            if group not in raw_columns:
                raw_columns.append(group)

        time_grain = normalize_time_grain(
            (source.get("extras") or {}).get("time_grain_sqla"),
            catalog=time_grains,
        )
        granularity = source.get("granularity") or source.get("granularity_sqla")

        result: list[CanonicalQueryColumn] = []
        seen: set[str] = set()
        for col in raw_columns:
            name, grain, expression = self._column_ref(col, time_grains=time_grains)
            if not name or name in seen:
                continue
            seen.add(name)
            if grain is None and granularity and name == granularity:
                grain = time_grain
            elif grain is None and time_grain and col is raw_columns[0]:
                # Timeseries: temporal x-axis often first; grain lives in extras.
                if isinstance(col, dict) and col.get("columnType") == "BASE_AXIS":
                    grain = time_grain
            result.append(
                CanonicalQueryColumn(
                    column_name=name,
                    time_grain=grain,
                    expression=expression,
                )
            )
        return result

    def _column_ref(
        self,
        col: Any,
        *,
        time_grains: TimeGrainCatalog | None = None,
    ) -> tuple[str | None, str | None, str | None]:
        """Return (name, time_grain, expression) for a Superset column ref.

        Physical columns are strings or dicts with column_name.
        Adhoc columns (Superset AdhocColumn) have label + sqlExpression.
        """
        if col is None:
            return None, None, None
        if isinstance(col, str):
            return col, None, None
        if isinstance(col, dict):
            sql_expression = (col.get("sqlExpression") or "").strip() or None
            # Adhoc: prefer label (chart-facing name); physical: column_name.
            if sql_expression and col.get("label"):
                name = col.get("label")
            else:
                name = (
                    col.get("column_name")
                    or col.get("label")
                    or col.get("name")
                    or sql_expression
                )
            grain = normalize_time_grain(
                col.get("timeGrain") or col.get("time_grain"),
                catalog=time_grains,
            )
            # Calculated physical columns may also carry expression.
            expression = sql_expression or (
                (col.get("expression") or "").strip() or None
            )
            return name, grain, expression
        return str(col), None, None

    def _map_query_metrics(
        self,
        source: dict[str, Any],
        adhoc_metrics_by_label: dict[str, CanonicalMetric],
    ) -> list[CanonicalQueryMetric]:
        result: list[CanonicalQueryMetric] = []
        for metric in source.get("metrics") or []:
            if isinstance(metric, str):
                adhoc = adhoc_metrics_by_label.get(metric)
                result.append(
                    CanonicalQueryMetric(
                        metric_name=metric,
                        expression=adhoc.expression if adhoc else None,
                        source_id=adhoc.source_id if adhoc else None,
                    )
                )
                continue
            if isinstance(metric, dict):
                adapted = self.to_adhoc_metric(metric)
                result.append(
                    CanonicalQueryMetric(
                        metric_name=adapted.name,
                        expression=adapted.expression,
                        source_id=adapted.source_id,
                    )
                )
        return result

    def _map_query_filters(
        self,
        source: dict[str, Any],
        unsupported: list[dict[str, Any]],
    ) -> list[CanonicalQueryFilter]:
        filters: list[CanonicalQueryFilter] = []

        for clause in source.get("filters") or []:
            mapped = self._structured_filter(clause)
            if mapped is None:
                unsupported.append(
                    {
                        "field": "filters",
                        "reason": "unrecognized filter clause",
                        "value": clause,
                    }
                )
            else:
                filters.append(mapped)

        extras = source.get("extras") or {}
        where_sql = (extras.get("where") or "").strip()
        having_sql = (extras.get("having") or "").strip()
        if where_sql:
            filters.append(
                CanonicalQueryFilter(
                    clause=FilterClause.WHERE,
                    filter_type=FilterType.EXPRESSION,
                    expression=where_sql,
                )
            )
        if having_sql:
            filters.append(
                CanonicalQueryFilter(
                    clause=FilterClause.HAVING,
                    filter_type=FilterType.EXPRESSION,
                    expression=having_sql,
                )
            )

        time_range = source.get("time_range")
        if time_range and time_range != NO_TIME_RANGE:
            already = any(f.operator == FilterOperator.TEMPORAL_RANGE for f in filters)
            if not already:
                granularity = source.get("granularity") or source.get(
                    "granularity_sqla"
                )
                filters.append(
                    CanonicalQueryFilter(
                        clause=FilterClause.WHERE,
                        filter_type=FilterType.STRUCTURED,
                        operator=FilterOperator.TEMPORAL_RANGE,
                        value=time_range,
                        column_name=(
                            granularity if isinstance(granularity, str) else None
                        ),
                    )
                )

        return filters

    def _structured_filter(
        self,
        clause: dict[str, Any],
    ) -> CanonicalQueryFilter | None:
        col = clause.get("col")
        op = clause.get("op")
        val = clause.get("val")
        if col is None or op is None:
            return None

        operator = _OPERATOR_MAP.get(str(op))
        if operator is None:
            # Preserve analytically meaningful unknown operators as expressions.
            return CanonicalQueryFilter(
                clause=FilterClause.WHERE,
                filter_type=FilterType.EXPRESSION,
                expression=f"{col} {op} {val!r}",
                column_name=str(col) if not isinstance(col, dict) else None,
            )

        column_name: str | None
        if isinstance(col, dict):
            column_name = (
                col.get("column_name") or col.get("sqlExpression") or col.get("label")
            )
        else:
            column_name = str(col)

        return CanonicalQueryFilter(
            clause=FilterClause.WHERE,
            filter_type=FilterType.STRUCTURED,
            operator=operator,
            value=val,
            column_name=column_name,
        )

    def _adhoc_filter_to_query_filter(
        self,
        adhoc: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Normalize an Explore adhoc filter into query-object filter shape."""
        expression_type = (adhoc.get("expressionType") or "").upper()
        if expression_type == "SQL":
            return None  # handled via extras when built by Superset
        subject = adhoc.get("subject")
        operator = adhoc.get("operator")
        if subject is None or operator is None:
            return None
        return {
            "col": subject,
            "op": operator,
            "val": adhoc.get("comparator"),
        }

    def _map_query_orders(
        self,
        source: dict[str, Any],
        unsupported: list[dict[str, Any]],
    ) -> list[CanonicalQueryOrder]:
        orders: list[CanonicalQueryOrder] = []
        for position, item in enumerate(source.get("orderby") or []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                unsupported.append(
                    {
                        "field": "orderby",
                        "reason": "unexpected orderby shape",
                        "value": item,
                    }
                )
                continue
            target, ascending = item[0], bool(item[1])
            column_name: str | None = None
            metric_name: str | None = None
            expression: str | None = None

            if isinstance(target, str):
                # Ambiguous: could be column or metric label; persistence resolves
                # against both registries (metric first, then column), creating
                # if needed — matching Superset orderby resolution order.
                column_name = target
                metric_name = target
            elif isinstance(target, dict):
                if target.get("expressionType") or target.get("aggregate"):
                    metric_name = target.get("label") or target.get("metric_name")
                    if (target.get("expressionType") or "").upper() == "SQL":
                        expression = target.get("sqlExpression")
                    elif target.get("aggregate"):
                        column = target.get("column") or {}
                        col_name = (
                            column.get("column_name") or column.get("columnName") or ""
                        )
                        aggregate = target.get("aggregate") or "SUM"
                        expression = (
                            f"{aggregate}({col_name})" if col_name else aggregate
                        )
                else:
                    sql_expression = (target.get("sqlExpression") or "").strip() or None
                    column_name = (
                        target.get("column_name")
                        or target.get("label")
                        or sql_expression
                    )
                    expression = sql_expression or (
                        (target.get("expression") or "").strip() or None
                    )
            else:
                unsupported.append(
                    {
                        "field": "orderby",
                        "reason": "unsupported order target type",
                        "value": target,
                    }
                )
                continue

            orders.append(
                CanonicalQueryOrder(
                    column_name=column_name,
                    metric_name=metric_name,
                    expression=expression,
                    asc=ascending,
                    position=position,
                )
            )
        return orders
