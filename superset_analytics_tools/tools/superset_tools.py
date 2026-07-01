from langchain_core.tools import tool

from ..services.chart_detail_service import ChartDetailService
from ..services.chart_list import ChartListService
from ..services.chart_data_service import ChartDataService
from ..services.evidence_chart_service import EvidenceChartService
from ..schemas.superset_schemas import AppliedFilter

_chart_list_service = ChartListService()
_chart_detail_service = ChartDetailService()
_chart_data_service = ChartDataService()
_evidence_chart_service = EvidenceChartService()


@tool
def get_chart_list() -> list[dict]:
    """List all available Superset charts.

    Returns each chart's id (uuid), name, and viz_type.
    Histogram charts are excluded from the results.
    """
    charts = _chart_list_service.get_chart_list()
    return [chart.model_dump() for chart in charts]


@tool
def get_chart_detail(chart_id: int) -> dict:
    """Fetch full metadata and sample data for a Superset chart.

    Args:
        chart_id: The chart's uuid identifier.

    Returns chart name, viz_type, metrics, available/applied/locked filters,
    and data samples with column profiles.
    """
    detail = _chart_detail_service.get(chart_id)
    return detail.model_dump()


@tool
def get_chart_detail_without_analysis(chart_id: str) -> dict:
    """Fetch full metadata and sample data for a Superset chart.

    Args:
        chart_id: The chart's uuid identifier.

    Returns chart name, viz_type, metrics, available/applied/locked filters,
    and data samples with column profiles.
    """
    detail = _chart_detail_service.get(chart_id, include_possible_analysis=False)
    return detail.model_dump()


@tool
def generate_evidence_chart(
    chart_id: int,
    interpretation: str,
    filters: list[AppliedFilter],
) -> dict:
    """
    Generate and save a frontend-ready evidence chart for an investigation.

    This tool fetches the filtered data for the original Superset chart,
    rebuilds it into the evidence-chart JSON format, saves the chart payload,
    and returns only the saved visualization ID plus the interpretation.

    Use this tool only when the original Superset chart uses one of the
    supported visualization types.

    Supported Superset viz_type values:
    - mixed_timeseries
    - echarts_timeseries_line
    - echarts_timeseries_smooth
    - echarts_timeseries_bar
    - echarts_timeseries_scatter

    Chart behavior:
    - Line and smooth line charts are rendered as line evidence charts.
    - Bar charts are rendered as bar evidence charts.
    - Scatter plots are rendered as scatter evidence charts.
    - Mixed time-series charts preserve query A and query B series, including
      line/bar/scatter mark type, stacking, and secondary-axis settings when
      available from Superset params.
    - The chart must use the same filtered data used in the investigation.
    - Do not call this tool for unsupported Superset chart types.

    Args:
        chart_id:
            Numeric ID of the original Superset chart.

        interpretation:
            Business-friendly explanation of what the evidence chart proves
            or supports. This text is attached to the saved chart and shown
            by the frontend.

        filters:
            The exact filters used during the investigation before fetching
            chart data.

    Returns:
        A dictionary with:
        - viz_id: ID of the saved evidence-chart JSON file.
        - interpretation: The same interpretation text provided by the agent.
    """
    data = _chart_data_service.get(chart_id, filters)        
    return _evidence_chart_service.get(chart_id, interpretation, data)