from uuid import uuid4

from ..client import superset_client
from ..constants import superset_consts
from ..parsers.sample_parser import get_possible_analysis
from ..schemas.superset_schemas import QueryColumnInfo, SQLExecutionResponse


class SQLExecutionService:
    def execute_sql(self, database_id, sql, query_limit=1000):
        data = superset_client.execute_sql(database_id, sql, query_limit).get("data", {})
        return data

    def execute_sql_and_build_sample_data(
        self, database_id, sql, query_limit=1000
    ) -> tuple[SQLExecutionResponse, list[dict]]:
        execution_id = str(uuid4())

        res = superset_client.execute_sql(database_id, sql, query_limit)

        data = res.get("data") or []
        columns = res.get("selected_columns") or []
        columns_serialized = [
            QueryColumnInfo(name=c.get("name"), dtype=c.get("type")) for c in columns
        ]
        sample_rows = data[:3]

        time_cols = [
            c.get("name")
            for c in columns
            if c.get("type_generic") == int(superset_consts.DTypeMapping.TEMPORAL)
        ]
        numerical_cols = [
            c.get("name")
            for c in columns
            if c.get("type_generic") == int(superset_consts.DTypeMapping.NUMERIC)
        ]
        categorical_cols = [
            c.get("name")
            for c in columns
            if c.get("type_generic") == int(superset_consts.DTypeMapping.STRING)
        ]

        possible_analysis = get_possible_analysis(
            time_cols, numerical_cols, categorical_cols
        )

        response = SQLExecutionResponse(
            execution_id=execution_id,
            row_count=len(data),
            columns=columns_serialized,
            sample_rows=sample_rows,
            possible_analysis=possible_analysis,
        )

        return response, data
