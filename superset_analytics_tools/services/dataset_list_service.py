from ..client import superset_client
from ..schemas import superset_schemas

class DatasetListService:
    def _fetch_dataset_list(self):
        max_pages = 10000
        page_size = 30
        results: list[superset_schemas.DatasetListItem] = []
        for page in range(max_pages):
            res = superset_client.get_dataset_list(page=page, page_size=page_size)
            for item in res:
                sql = item.get("sql")
                table = item.get("table_name")
                kind = item.get("kind")
                
                if not sql: 
                    schema = item.get("schema")
                    
                    sql = f"{schema}.{table}"
                    
                results.append(superset_schemas.DatasetListItem(
                    id=item.get("id"),
                    name=table,
                    description=item.get("description"),
                    table=sql,
                    kind=kind,
                ))
                
            if len(res) < page_size:
                break
            
        return results
    
 
    def get_dataset_list(self) -> list[superset_schemas.DatasetListItem]:
        results = self._fetch_dataset_list()
        return results
    
