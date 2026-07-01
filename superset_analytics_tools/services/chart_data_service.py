import json

from ..client.superset_client import get_chart_data_table , get_chart
from ..schemas.superset_schemas import AppliedFilter

class ChartDataService:         
    def get(self, chart_id: int, filters: list[AppliedFilter]) -> list[dict]:
        res = get_chart(chart_id)
        
        query_context = json.loads(res.get("query_context"))
        
        for q in query_context.get("queries"):
            q["filters"] = [f.model_dump() for f in filters]

        res = get_chart_data_table(query_context)
        data = [d.get("data", []) for d in res]
        
        if len(data) == 1:
            return {"data_1": data[0], "data_2": None} 
        
        return {"data_1": data[0], "data_2": data[1]}
