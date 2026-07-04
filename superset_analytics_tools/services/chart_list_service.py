from ..client import superset_client
from ..schemas import superset_schemas
from ..constants import superset_consts

class ChartListService:
    def _fetch_chart_list(self): 
        ignore_datasource_ids = [
            47, 
            46,
            44, 
            45, 
            42, 
            43,  
            41, 
            39
        ]
        duplicate_names = []
        max_pages = 5000
        page_size = 20
        results: list[superset_schemas.ChartList] = []
        for page in range(max_pages):
            res = superset_client.get_chart_list(page=page, page_size=page_size) 
          
            
            for item in res:
                if item.get("slice_name") in duplicate_names:
                    continue
                
                if item.get("datasource_id") in ignore_datasource_ids:
                    continue
                
                duplicate_names.append(item.get("slice_name"))
                
                results.append(
                    superset_schemas.ChartList(
                        id=item.get("id"),
                        viz_type=item.get("viz_type"),
                        name=item.get("slice_name"),
                    )
                )   
            
            if len(res) < page_size:
                break
        return results

            
    def _filter_chart_list(self, chart_list: list[superset_schemas.ChartList]):
        exclude_viz_types = [superset_consts.VizType.HISTOGRAM, 'deck_scatter']
        
        return [chart for chart in chart_list if chart.viz_type not in exclude_viz_types]
        
    def get_chart_list(self) -> list[superset_schemas.ChartList]:
        chart_list = self._fetch_chart_list()
        filtered_chart_list = self._filter_chart_list(chart_list)
        # return chart_list
        return filtered_chart_list