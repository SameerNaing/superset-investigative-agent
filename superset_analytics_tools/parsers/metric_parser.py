from ..schemas import superset_schemas


def _parse_metric_list(metrics):
    parsed = []
    for metric in metrics:
        m = {"label": metric.get("label", "")}
        column = metric.get("column")
        if column is not None:
            m["column_name"] = column.get("column_name")
            m["aggregate"] = metric.get("aggregate")
        else:
            m["sql_expression"] = metric.get("sqlExpression")
        parsed.append(superset_schemas.Metric(**m))
    return parsed


def parse_metrics(metric_a, metrics_b=None):
    if not metric_a:
        return []

    metrics = _parse_metric_list(metric_a)
    if metrics_b is not None:
        return [metrics, _parse_metric_list(metrics_b)]
    return metrics
