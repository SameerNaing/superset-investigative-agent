from ..client import superset_client
from ..parsers import parse_metrics
from ..extractors import extract_chart_metrics
from ..schemas import superset_schemas

class DatasetDetailService:
    def _get_charts_metrics(self, charts): 
        metrics = []
        
        for chart in charts:
            chart_detail = superset_client.get_chart_detail(chart.id)
            chart_detail = chart_detail.get("result", {})
            
            form_data = chart_detail.get("form_data", {})
            
            metrics, metrics_b = extract_chart_metrics(form_data)
            
            metrics.extend(parse_metrics(metrics))
            if metrics_b is not None:
                metrics.extend(parse_metrics(metrics_b))
            
        return metrics
    
    def _map_columns(self, columns): 
        cols = []
        
        for col in columns:
            expression = (col.get("expression") or "").strip()

            cols.append(
                superset_schemas.DatasetColumn(
                    name=col.get("column_name"),
                    type=col.get("type"),
                    description=col.get("description"),
                    is_calculated=bool(expression),
                    expression=expression or None,
                    filterable=col.get("filterable", False),
                    groupby=col.get("groupby", False),
                    is_time=col.get("is_dttm", False),
                )
            )
            
        return cols
    
    
    def get(self, dataset_id):
        detail = superset_client.get_dataset_detail(dataset_id)
        columns = detail.get("columns", []) 
        
        table = detail.get("sql")
        kind = detail.get("kind")
        
        if not table: 
            schema = detail.get("schema") 
            table_name = detail.get("table_name")
            table = f"{schema}.{table_name}"
            
        db_id = detail.get("database", {}).get("id")
        
        charts = superset_client.get_chart_list(datasource_id=dataset_id)
        charts = [superset_schemas.ChartList(id=chart.get("id"), name=chart.get("slice_name"), viz_type=chart.get("viz_type")) for chart in charts]
        
        columns = self._map_columns(columns)
        metrics = self._get_charts_metrics(charts)
        
        
        return superset_schemas.DatasetDetail(
            id=dataset_id, 
            columns=columns,
            table=table, 
            db_connection_id=db_id, 
            charts=charts, 
            metrics=metrics,
            kind=kind)