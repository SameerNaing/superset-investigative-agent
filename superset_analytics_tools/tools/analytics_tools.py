from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ..services import AnomalyService, ChartDataService, AnalyticsSummaryService, QueryResultStoreService, query_memory_service
from ..schemas.superset_schemas import AppliedFilter
from ..constants.consts import QueryType
from ..schemas.analytics_schemas import AnalyticsError, AnalyticsDataSource


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


def _load_analytics_data(
    source: AnalyticsDataSource,
) -> list[dict]:
    if source.source_type == "chart":
        if source.chart_id is None:
            raise ValueError(
                "chart_id is required when source_type is 'chart'."
            )

        data = _chart_data_service.get(
            source.chart_id,
            source.filter,
            source.time_grain,
        )

        return _check_get_data(data, source.query_type)

    if source.source_type == "sql_execution":
        stored_result = query_memory_service.get(source.execution_id)
        return stored_result.data

    raise ValueError(
        f"Unsupported analytics source type: {source.source_type}"
    )


@tool
def detect_timeseries_anomalies(
    source: AnalyticsDataSource,
    time_col: str,
    summary_question: str,
    metric_col: str,
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
        source: Reference describing where the analytics data should be
            loaded from (a Superset chart or a stored SQL execution result).
        time_col: Name of the timestamp column.
        summary_question: The original user question used to focus the
            generated explanation.
        metric_col: Name of the numeric metric to analyze.

    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data (small datasets) or statistical
        anomaly detection (larger datasets). 
    """
    data = _load_analytics_data(source)

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
    source: AnalyticsDataSource,
    category_col: str,
    summary_question: str,
    metric_col: str,
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
        source: Reference describing where the analytics data should be
            loaded from (a Superset chart or a stored SQL execution result).
        category_col: Name of the categorical column to compare.
        summary_question: The original user question used to focus the
            generated explanation.
        metric_col: Name of the numeric metric to compare across categories.
    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data or cross-section anomaly detection.
    """
    data = _load_analytics_data(source)

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
    source: AnalyticsDataSource,
    x_col: str,
    summary_question: str,
    y_col: str,
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
        source: Reference describing where the analytics data should be
            loaded from (a Superset chart or a stored SQL execution result).
        x_col: Name of the independent/predictor numeric column.
        summary_question: The original user question used to focus the
            generated explanation.
        y_col: Name of the dependent/outcome numeric column.
    Returns:
        A concise natural-language explanation that answers the user's
        question using either the raw data or relationship anomaly detection.
    """
    data = _load_analytics_data(source)

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