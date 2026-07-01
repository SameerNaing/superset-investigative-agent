from ..client import superset_client
from ..schemas import superset_schemas


def _parse_adhoc_filter_group(filters):
    locked = []
    simple_cols = []
    for f in filters or []:
        sql_expression = f.get("sqlExpression")
        if sql_expression is not None:
            locked.append(
                superset_schemas.LockedFilters(
                    clause=f.get("clause"),
                    sql=sql_expression,
                )
            )
            continue
        simple_cols.append(f.get("subject"))
    return locked, simple_cols


def parse_adhoc_filters(filter_a, filter_b=None):
    locked, simple_cols = _parse_adhoc_filter_group(filter_a)
    if filter_b is not None:
        locked_b, simple_cols_b = _parse_adhoc_filter_group(filter_b)
        simple_cols.extend(simple_cols_b)
        locked = [locked, locked_b]
    return locked, simple_cols


def normalize_locked_filters(locked):
    if not locked:
        return None
    if isinstance(locked[0], list):
        return locked if any(locked) else None
    return locked


def parse_applied_filters(queries):
    parsed = [
        [
            superset_schemas.AppliedFilter(
                col=f.get("col"),
                op=f.get("op"),
                val=f.get("val"),
            )
            for f in query.get("filters", [])
        ]
        for query in queries
    ]
    return parsed[0] if len(parsed) == 1 else parsed


def build_available_filters(columns, col_dtype_ref, datasource_id):
    available_filters = []
    for col in columns:
        datatype = col_dtype_ref.get(col)
         # some filter dtype is getting None  (eg. chart_id:121, Load Unit Queue Time Avg, col: latest_shift_for_cycle)
        if datatype is None:
            continue
        filter_def = {"col": col, "dtype": datatype}
        if datatype in ("STRING", "TEXT"):
            filter_def["available_values"] = superset_client.get_filter_values(
                datasource_id, col
            )
       
        
        available_filters.append(superset_schemas.AvailableFilter(**filter_def))
    return available_filters
