from ..constants import superset_consts


def extract_chart_metrics(form_data):
    viz_type = form_data.get("viz_type")
    metrics = form_data.get("metrics")
    if viz_type in [superset_consts.VizType.BIG_NUMBER_TOTAL, superset_consts.VizType.SANKEY]:
        metrics = [form_data.get("metric")]
    if viz_type == superset_consts.VizType.GANTT:
        metrics = form_data.get("tooltip_metrics")

    metrics_b = form_data.get("metrics_b")
    return metrics, metrics_b
