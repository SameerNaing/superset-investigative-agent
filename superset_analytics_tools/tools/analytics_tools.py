from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ..services import AnomalyService, ChartDataService, AnalyticsSummaryService
from ..schemas.superset_schemas import AppliedFilter
from ..constants.consts import QueryType
from ..schemas.analytics_schemas import AnalyticsError


_anomaly_service = AnomalyService()
_chart_data_service = ChartDataService()
_summary_service = AnalyticsSummaryService(
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
    max_summary_rows=20,
)


def _serialize_result(result) -> dict:
    return result.model_dump()


def _check_get_data(data: dict, query_type: QueryType | None) -> dict:
    if data.get("data_2") and query_type is None:
        raise ValueError(
            "The chart has two queries, but no query type was provided. "
            "Please provide a query type."
        )

    if query_type == QueryType.QUERY_A:
        return data.get("data_1")
    elif query_type == QueryType.QUERY_B:
        return data.get("data_2")
    else:
        return data.get("data_1")


@tool
def detect_timeseries_anomalies(
    chart_id: int,
    filter: list[AppliedFilter],
    time_col: str,
    summary_question: str,
    metric_col: str,
    time_grain: str = None,
    query_type: QueryType | None = None,
) -> str:
    """
    Analyze a time-series metric and explain its behaviour over time.

    Use this tool when the data contains a timestamp column and a numeric
    metric, and the user wants to understand trends, unusual behaviour,
    spikes, drops, or changes over time.

    This tool automatically adapts to the amount of data:
    - For small datasets, it summarizes the raw data using the user's
      question as context.
    - For larger datasets, it performs statistical anomaly detection and
      returns a concise natural-language interpretation of the findings.

    Args:
        chart_id: Numeric ID of the Superset chart.
        filter: Filters to apply before fetching chart data.
        time_col: Name of the timestamp column.
        summary_question: The original user question used to focus the
            generated explanation.
        metric_col: Name of the numeric metric to analyze.
        query_type: Required only for Mixed charts containing two queries.
        time_grain: The time grain to use for the chart.

    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data (small datasets) or statistical
        anomaly detection (larger datasets). 
    """
    data = _chart_data_service.get(chart_id, filter, time_grain)
    data = _check_get_data(data, query_type)

    try:
        result = _anomaly_service.detect_timeseries(
            data,
            time_col,
            metric_col,
            max_anomalies=100,
        )

        if isinstance(result, AnalyticsError):
            return _summary_service.summarize_raw_data(data, summary_question)

        serialized = _serialize_result(result)
        return _summary_service.summarize_analytics(serialized, summary_question)
    except Exception as e:
        return f"Error while analyzing time-series anomalies: {e}"




@tool
def detect_cross_section_anomalies(
    chart_id: int,
    filter: list[AppliedFilter],
    category_col: str,
    summary_question: str,
    metric_col: str,
    query_type: QueryType | None = None,
    time_grain: str = None,
) -> str:
    """
    Analyze a metric across categories and explain unusual category-level values.

    Use this tool when the data contains a categorical column and a numeric
    metric, and the user wants to compare groups, find unusual categories,
    or understand which groups are higher or lower than peers.

    This tool automatically adapts to the amount of data:
    - For small datasets, it summarizes the raw data using the user's
      question as context.
    - For larger datasets, it performs cross-section anomaly detection and
      returns a concise natural-language interpretation of the findings.

    Args:
        chart_id: Numeric ID of the Superset chart.
        filter: Filters to apply before fetching chart data.
        category_col: Name of the categorical column to compare.
        summary_question: The original user question used to focus the
            generated explanation.
        metric_col: Name of the numeric metric to compare across categories.
        query_type: Required only for Mixed charts containing two queries.
        time_grain: The time grain to use for the chart.
    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data or cross-section anomaly detection.
    """
    data = _chart_data_service.get(chart_id, filter, time_grain)
    data = _check_get_data(data, query_type)

    try:
        result = _anomaly_service.detect_cross_section(
            data,
            category_col,
            metric_col,
            max_anomalies=100,
        )

        if isinstance(result, AnalyticsError):
            return _summary_service.summarize_raw_data(data, summary_question)

        serialized = _serialize_result(result)
        return _summary_service.summarize_analytics(serialized, summary_question)
    except Exception as e:
        return f"Error while analyzing cross-section anomalies: {e}"


@tool
def detect_relationship_anomalies(
    chart_id: int,
    filter: list[AppliedFilter],
    x_col: str,
    summary_question: str,
    y_col: str,
    query_type: QueryType | None = None,
    time_grain: str = None,
) -> str:
    """
    Analyze the relationship between two numeric columns and explain unusual
    deviations from the expected pattern.

    Use this tool when the data contains two numeric columns and the user wants
    to understand correlation, relationship strength, unusual points, or cases
    where one metric does not behave as expected relative to another.

    This tool automatically adapts to the amount of data:
    - For small datasets, it summarizes the raw data using the user's
      question as context.
    - For larger datasets, it performs relationship anomaly detection and
      returns a concise natural-language interpretation of the findings.

    Args:
        chart_id: Numeric ID of the Superset chart.
        filter: Filters to apply before fetching chart data.
        x_col: Name of the independent/predictor numeric column.
        summary_question: The original user question used to focus the
            generated explanation.
        y_col: Name of the dependent/outcome numeric column.
        query_type: Required only for Mixed charts containing two queries.
        time_grain: The time grain to use for the chart.
    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data or relationship anomaly detection.
    """
    data = _chart_data_service.get(chart_id, filter, time_grain)
    data = _check_get_data(data, query_type)

    try:
        result = _anomaly_service.detect_relationship(
            data,
            x_col,
            y_col,
            max_anomalies=100,
        )

        if isinstance(result, AnalyticsError):
            return _summary_service.summarize_raw_data(data, summary_question)

        serialized = _serialize_result(result)
        return _summary_service.summarize_analytics(serialized, summary_question)
    except Exception as e:
        return f"Error while analyzing relationship anomalies: {e}"