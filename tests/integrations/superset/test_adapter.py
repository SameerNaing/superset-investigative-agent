"""Focused adapter mapping tests (no HTTP / DB)."""

from __future__ import annotations

from app.db.models.query import FilterClause, FilterOperator, FilterType
from app.db.models.visualization import VizType
from app.integrations.superset.adapter import SupersetAdapter
from app.integrations.superset.time_grains import (
    TimeGrainCatalog,
    normalize_time_grain,
    slugify_grain_label,
)

SAMPLE_TIME_GRAIN_SQLA = [
    ["PT1H", "Hour"],
    ["P1D", "Day"],
    ["P3M", "Quarter"],
    ["P1M", "Month"],
    ["SHIFT_AM", "Morning Shift"],
]


class TestTimeGrainCatalog:
    def test_parses_dataset_time_grain_sqla(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(SAMPLE_TIME_GRAIN_SQLA)
        assert catalog.resolve("PT1H") == "hour"
        assert catalog.resolve("P1D") == "day"
        assert catalog.resolve("P3M") == "quarter"
        assert catalog.resolve("SHIFT_AM") == "morning_shift"

    def test_custom_addon_duration_is_not_hardcoded(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(
            [["PT8H", "Night Shift"], ["P1D", "Day"]]
        )
        assert catalog.resolve("PT8H") == "night_shift"
        assert catalog.duration_for_name("night_shift") == "PT8H"

    def test_already_canonical_slug(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(SAMPLE_TIME_GRAIN_SQLA)
        assert catalog.resolve("month") == "month"
        assert catalog.resolve("Morning Shift") == "morning_shift"

    def test_unknown_without_catalog_keeps_raw_duration(self):
        assert normalize_time_grain("PT1H") == "PT1H"
        assert normalize_time_grain("SHIFT_AM") == "SHIFT_AM"

    def test_unknown_in_catalog_keeps_raw_value(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla([["P1D", "Day"]])
        assert catalog.resolve("PT99H") == "PT99H"

    def test_none_and_blank(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(SAMPLE_TIME_GRAIN_SQLA)
        assert normalize_time_grain(None, catalog) is None
        assert normalize_time_grain("  ", catalog) is None

    def test_skips_null_duration(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(
            [[None, "Original"], ["P1D", "Day"]]
        )
        assert catalog.resolve("P1D") == "day"
        assert catalog.duration_for_name("original") is None

    def test_roundtrip_records(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(SAMPLE_TIME_GRAIN_SQLA)
        restored = TimeGrainCatalog.from_records(catalog.to_records())
        assert restored.resolve("SHIFT_AM") == "morning_shift"

    def test_slugify(self):
        assert slugify_grain_label("Hour") == "hour"
        assert slugify_grain_label("Week starting Sunday") == "week_starting_sunday"
        assert slugify_grain_label("5 minute") == "5_minute"


class TestDatasetMapping:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_column_mapping(self):
        col = self.adapter.to_dataset_column(
            {
                "id": 12,
                "column_name": "material_type",
                "type": "STRING",
                "is_dttm": False,
                "expression": "",
                "description": "Material",
            }
        )
        assert col.source_id == "12"
        assert col.name == "material_type"
        assert col.data_type == "STRING"
        assert col.is_temporal is False
        assert col.expression is None

    def test_calculated_column(self):
        col = self.adapter.to_dataset_column(
            {
                "id": 13,
                "column_name": "shift_label",
                "type": "STRING",
                "is_dttm": False,
                "expression": "CASE WHEN hour < 12 THEN 'AM' ELSE 'PM' END",
            }
        )
        assert col.expression.startswith("CASE WHEN")

    def test_saved_metric(self):
        metric = self.adapter.to_metric(
            {
                "id": 7,
                "metric_name": "production_bcm",
                "verbose_name": "Production BCM",
                "expression": "SUM(bcm)",
                "description": "Total BCM",
            }
        )
        assert metric.source_id == "7"
        assert metric.name == "Production BCM"
        assert metric.expression == "SUM(bcm)"

    def test_adhoc_simple_metric(self):
        metric = self.adapter.to_adhoc_metric(
            {
                "expressionType": "SIMPLE",
                "aggregate": "SUM",
                "column": {"column_name": "bcm"},
                "label": "Sum BCM",
            }
        )
        assert metric.expression == "SUM(bcm)"
        assert metric.name == "Sum BCM"
        assert metric.source_id is None

    def test_adhoc_sql_metric(self):
        metric = self.adapter.to_adhoc_metric(
            {
                "expressionType": "SQL",
                "sqlExpression": "SUM(bcm) / NULLIF(SUM(hours), 0)",
                "label": "Rate",
            }
        )
        assert "NULLIF" in metric.expression


class TestFilterMapping:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_structured_eq(self):
        filt = self.adapter._structured_filter(
            {"col": "material_type", "op": "==", "val": "ORE"}
        )
        assert filt is not None
        assert filt.filter_type == FilterType.STRUCTURED
        assert filt.operator == FilterOperator.EQ
        assert filt.value == "ORE"
        assert filt.column_name == "material_type"

    def test_in_filter(self):
        filt = self.adapter._structured_filter(
            {"col": "truck", "op": "IN", "val": ["T1", "T2"]}
        )
        assert filt is not None
        assert filt.operator == FilterOperator.IN

    def test_temporal_range(self):
        filt = self.adapter._structured_filter(
            {"col": "event_time", "op": "TEMPORAL_RANGE", "val": "Last month"}
        )
        assert filt is not None
        assert filt.operator == FilterOperator.TEMPORAL_RANGE
        assert filt.value == "Last month"

    def test_extras_where_having(self):
        query, _ = self.adapter.to_query(
            {
                "columns": ["material_type"],
                "metrics": ["production"],
                "filters": [],
                "extras": {
                    "where": "(status = 'active')",
                    "having": "(SUM(bcm) > 1000)",
                },
            }
        )
        assert len(query.filters) == 2
        where = next(f for f in query.filters if f.clause == FilterClause.WHERE)
        having = next(f for f in query.filters if f.clause == FilterClause.HAVING)
        assert where.filter_type == FilterType.EXPRESSION
        assert having.expression == "(SUM(bcm) > 1000)"


class TestOrderAndLimit:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_orderby_and_row_limit(self):
        query, _ = self.adapter.to_query(
            {
                "columns": ["material_type"],
                "metrics": ["Production BCM"],
                "orderby": [["Production BCM", False], ["material_type", True]],
                "row_limit": 50,
            }
        )
        assert query.row_limit == 50
        assert len(query.orders) == 2
        assert query.orders[0].asc is False
        assert query.orders[0].position == 0
        assert query.orders[1].asc is True

    def test_adhoc_column_preserves_label_and_expression(self):
        query, _ = self.adapter.to_query(
            {
                "columns": [
                    {
                        "expressionType": "SQL",
                        "label": "Crew",
                        "sqlExpression": "crew_name",
                    }
                ],
                "metrics": [],
            }
        )
        assert len(query.columns) == 1
        assert query.columns[0].column_name == "Crew"
        assert query.columns[0].expression == "crew_name"

    def test_custom_addon_time_grain_from_catalog(self):
        catalog = TimeGrainCatalog.from_time_grain_sqla(
            [["SHIFT_AM", "Morning Shift"], ["P1D", "Day"]]
        )
        query, _ = self.adapter.to_query(
            {
                "columns": [
                    {
                        "column_name": "event_time",
                        "timeGrain": "SHIFT_AM",
                        "columnType": "BASE_AXIS",
                    }
                ],
                "metrics": ["production"],
                "extras": {"time_grain_sqla": "SHIFT_AM"},
            },
            time_grains=catalog,
        )
        assert query.columns[0].time_grain == "morning_shift"


class TestDatasetPlaceholders:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_skips_new_column_ui_placeholder(self):
        dataset = self.adapter.to_dataset(
            {
                "id": 14,
                "table_name": "production",
                "columns": [
                    {
                        "id": 1,
                        "column_name": "event_time",
                        "type": "TIMESTAMP",
                        "is_dttm": True,
                    },
                    {
                        "column_name": "<new column>",
                        "type": "UNKNOWN",
                        "expression": "<enter SQL expression here>",
                        "is_dttm": False,
                    },
                ],
                "metrics": [],
                "database": {"id": 1},
            }
        )
        assert len(dataset.columns) == 1
        assert dataset.columns[0].name == "event_time"


class TestMixedChartMapping:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_two_queries_one_analytic(self):
        chart = {
            "id": 74,
            "slice_name": "Production and Target",
            "description": "Mixed",
            "viz_type": "mixed_timeseries",
            "datasource_id": 12,
            "params": {
                "viz_type": "mixed_timeseries",
                "seriesType": "bar",
                "seriesTypeB": "line",
                "yAxisIndex": 0,
                "yAxisIndexB": 1,
                "metrics": [
                    {
                        "expressionType": "SQL",
                        "sqlExpression": "SUM(actual)",
                        "label": "Actual",
                    }
                ],
                "metrics_b": [
                    {
                        "expressionType": "SQL",
                        "sqlExpression": "SUM(target)",
                        "label": "Target",
                    }
                ],
            },
            "query_context": {
                "datasource": {"id": 12, "type": "table"},
                "queries": [
                    {
                        "columns": [
                            {
                                "column_name": "event_time",
                                "timeGrain": "P1D",
                                "columnType": "BASE_AXIS",
                            }
                        ],
                        "metrics": [
                            {
                                "expressionType": "SQL",
                                "sqlExpression": "SUM(actual)",
                                "label": "Actual",
                            }
                        ],
                        "filters": [{"col": "material_type", "op": "==", "val": "ORE"}],
                        "extras": {"time_grain_sqla": "P1D"},
                        "time_range": "Last month",
                        "row_limit": 10000,
                    },
                    {
                        "columns": [
                            {
                                "column_name": "event_time",
                                "timeGrain": "P1D",
                                "columnType": "BASE_AXIS",
                            }
                        ],
                        "metrics": [
                            {
                                "expressionType": "SQL",
                                "sqlExpression": "SUM(target)",
                                "label": "Target",
                            }
                        ],
                        "filters": [],
                        "extras": {"time_grain_sqla": "P1D"},
                        "time_range": "Last month",
                        "row_limit": 10000,
                    },
                ],
                "form_data": {
                    "viz_type": "mixed_timeseries",
                    "seriesType": "bar",
                    "seriesTypeB": "line",
                    "yAxisIndex": 0,
                    "yAxisIndexB": 1,
                },
            },
        }

        analytic = self.adapter.to_analytic(
            chart,
            time_grains=TimeGrainCatalog.from_time_grain_sqla(SAMPLE_TIME_GRAIN_SQLA),
        )
        assert analytic.source_id == "74"
        assert analytic.dataset_source_id == "12"
        assert len(analytic.queries) == 2
        assert analytic.queries[0].position == 0
        assert analytic.queries[1].position == 1
        assert analytic.queries[0].metrics[0].metric_name == "Actual"
        assert analytic.queries[1].metrics[0].metric_name == "Target"
        assert analytic.queries[0].columns[0].time_grain == "day"
        assert analytic.queries[0].filters[0].operator == FilterOperator.EQ
        assert analytic.visualization is not None
        assert analytic.visualization.viz_type == VizType.MIXED_CHART
        encodings = analytic.visualization.options["query_encodings"]
        assert encodings[0]["series_type"] == "bar"
        assert encodings[1]["series_type"] == "line"
        assert encodings[1]["y_axis_index"] == 1


class TestDatasetPayload:
    def setup_method(self):
        self.adapter = SupersetAdapter()

    def test_full_dataset(self):
        dataset = self.adapter.to_dataset(
            {
                "id": 12,
                "table_name": "production_daily",
                "schema": "mining",
                "kind": "physical",
                "description": "Daily production",
                "database": {"id": 1, "database_name": "warehouse"},
                "time_grain_sqla": [
                    ["P1D", "Day"],
                    ["SHIFT_AM", "Morning Shift"],
                ],
                "columns": [
                    {
                        "id": 1,
                        "column_name": "event_time",
                        "type": "TIMESTAMP",
                        "is_dttm": True,
                    },
                    {
                        "id": 2,
                        "column_name": "material_type",
                        "type": "VARCHAR",
                        "is_dttm": False,
                    },
                ],
                "metrics": [
                    {
                        "id": 9,
                        "metric_name": "production_bcm",
                        "verbose_name": "Production BCM",
                        "expression": "SUM(bcm)",
                    }
                ],
            }
        )
        assert dataset.source_id == "12"
        assert len(dataset.columns) == 2
        assert dataset.columns[0].is_temporal is True
        assert dataset.metrics[0].source_id == "9"
        assert dataset.extra["schema"] == "mining"
        assert dataset.extra["time_grains"] == [
            {"duration": "P1D", "label": "Day", "name": "day"},
            {
                "duration": "SHIFT_AM",
                "label": "Morning Shift",
                "name": "morning_shift",
            },
        ]


class TestColtypeMapping:
    def test_generic_data_types(self):
        from app.integrations.superset.types import (
            SUPERSET_COLTYPE_TO_DATA_TYPE,
            data_type_from_coltype,
        )

        assert data_type_from_coltype(0) == "NUMERIC"
        assert data_type_from_coltype(1) == "STRING"
        assert data_type_from_coltype(2) == "TEMPORAL"
        assert data_type_from_coltype(3) == "BOOLEAN"
        assert data_type_from_coltype(99) is None
        assert data_type_from_coltype(None) is None
        assert SUPERSET_COLTYPE_TO_DATA_TYPE[2] == "TEMPORAL"
