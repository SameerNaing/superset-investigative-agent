def extract_metric_columns(metrics):
    flat = metrics
    if metrics and isinstance(metrics[0], list):
        flat = [m for group in metrics for m in group]
    return list({m.column_name for m in flat if m.column_name})


def extract_query_columns(queries):
    cols = []
    for query in queries:
        for col in query.get("columns", []):
            if isinstance(col, str):
                cols.append(col)
    return list(set(cols))


def collect_filterable_columns(metrics, adhoc_cols, queries):
    columns = extract_metric_columns(metrics)
    columns.extend(adhoc_cols)
    columns.extend(extract_query_columns(queries))
    return list(set(columns))
