import json

from ..client import superset_client
from ..extractors import collect_filterable_columns, extract_chart_metrics
from ..parsers import (
    build_available_filters,
    build_sample_data,
    normalize_locked_filters,
    parse_adhoc_filters,
    parse_applied_filters,
    parse_metrics,
)
from ..schemas import superset_schemas


class ChartDetailService:
    def _get_time_grain_info(self, queries, time_grain_list):
        if len(queries) == 0:
            return None
        
        query = queries[0]
        
        time_grain_col = None
        for col in query.get('columns'):
            if type(col) != dict:
                continue 
            
            timegrain = col.get('timeGrain')
            if not timegrain:
                continue 
            
            time_grain_col = superset_schemas.TimeGrainInfo(
                col=col.get("sqlExpression"),
                current_val=col.get('timeGrain'),
                available_vals=time_grain_list
            )
            break    
        
        return time_grain_col
        
    def _load_chart(self, chart_id):
        res = superset_client.get_chart_detail(chart_id)
        result = res.get("result", {})

        dataset = result.get("dataset", {})
        columns = dataset.get("columns", [])
        col_dtype_ref = {col.get("column_name"): col.get("type") for col in columns}

        form_data = result.get("form_data", {})
        groupby = form_data.get("groupby", [])
        
        query_context = json.loads(result.get("slice", {}).get("query_context", "{}"))
        queries = query_context.get("queries", [])
        viz_type = form_data.get("viz_type")
        time_grain_list = {j: i for i,j in dataset.get("time_grain_sqla", {})}
        
      
        metrics, metrics_b = extract_chart_metrics(form_data)

        return {
            "col_dtype_ref": col_dtype_ref,
            "form_data": form_data,
            "query_context": query_context,
            "queries": queries,
            "time_grain_list": time_grain_list,
            "viz_type": viz_type,
            "datasource_id": query_context.get("datasource", {}).get("id"),
            "chart_name": result.get("slice", {}).get("slice_name"),
            "metrics": metrics,
            "metrics_b": metrics_b,
            "adhoc_filters": form_data.get("adhoc_filters") or [],
            "adhoc_filters_b": form_data.get("adhoc_filters_b"),
            "groupby": groupby,
        }

    def get(self, chart_id, include_possible_analysis=True) -> superset_schemas.ChartDetail:
        chart = self._load_chart(chart_id)
        
        dimensions = [
            superset_schemas.Dimension(
                name=g if isinstance(g, str) else g.get("label"),
                sql_expression=None if isinstance(g, str) else g.get("sqlExpression"),
            )
            for g in chart["groupby"]
        ]
        
        time_grain_info = self._get_time_grain_info(chart["queries"], chart["time_grain_list"])

        metrics = parse_metrics(chart["metrics"], chart["metrics_b"])
        locked_filters, adhoc_cols = parse_adhoc_filters(
            chart["adhoc_filters"], chart["adhoc_filters_b"]
        )
        locked_filters = normalize_locked_filters(locked_filters)
        applied_filters = parse_applied_filters(chart["queries"])

        columns = collect_filterable_columns(metrics, adhoc_cols, chart["queries"])
        available_filters = build_available_filters(
            columns, chart["col_dtype_ref"], chart["datasource_id"]
        )

        table_data = superset_client.get_chart_data_table(chart["query_context"])
        samples = [
            build_sample_data(row, chart["form_data"], chart["viz_type"], include_possible_analysis)
            for row in table_data
        ]
        if len(samples) == 1:
            samples = samples[0]

        return superset_schemas.ChartDetail(
            id=str(chart_id),
            name=chart["chart_name"],
            dimensions=dimensions,
            viz_type=chart["viz_type"],
            metrics=metrics,
            available_filters=available_filters,
            applied_filters=applied_filters,
            locked_filters=locked_filters,
            data_samples=samples,
            timegrain=time_grain_info,
        )
