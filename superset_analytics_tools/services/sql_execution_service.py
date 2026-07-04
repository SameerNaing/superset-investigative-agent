from ..client import superset_client

class SQLExecutionService:
    def execute_sql(self, database_id, sql, query_limit=1000):
        data =  superset_client.execute_sql(database_id, sql, query_limit).get("data", {})
        return data