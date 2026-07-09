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


def build_available_filters(col_dtype_ref: dict[str, str], datasource_id: int):
    
    """
    Build available filters from column data type reference and datasource ID.
    
    Args:
        col_dtype_ref: Dictionary mapping column names to their data types.
        datasource_id: The ID of the datasource to build filters for.
        
    Returns:
        List of AvailableFilter objects representing available filters.
    """
    
    available_filters = []
    for col, dtype in col_dtype_ref.items():
        if dtype is None:
            continue
        
        filter_def = {"col": col, "dtype": dtype}
        
        if dtype in ("STRING", "TEXT"):
            
            filter_def["available_values"] = superset_client.get_filter_values(
                datasource_id, col
            )
            
        available_filters.append(superset_schemas.AvailableFilter(**filter_def))
        
    return available_filters
