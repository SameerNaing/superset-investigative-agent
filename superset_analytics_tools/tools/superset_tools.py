from langchain_core.tools import tool

from superset_analytics_tools.schemas.superset_schemas import SQLExecutionResponse

from ..services import ChartDataService, ChartDetailService, ChartListService, EvidenceChartService, SQLExecutionService, DatasetListService, DatasetDetailService, QueryResultStoreService, query_memory_service
from ..schemas import AppliedFilter, DatasetDetail, DatasetListItem, DatasetDetail



_chart_list_service = ChartListService()
_chart_detail_service = ChartDetailService()
_chart_data_service = ChartDataService()
_evidence_chart_service = EvidenceChartService()
_sql_execution_service = SQLExecutionService()
_dataset_list_service = DatasetListService()
_dataset_detail_service = DatasetDetailService()

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
    time_grain: str = None,
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
        
        time_grain:
            The time grain to use for the chart.

    Returns:
        A dictionary with:
        - viz_id: ID of the saved evidence-chart JSON file.
        - interpretation: The same interpretation text provided by the agent.
    """
    data = _chart_data_service.get(chart_id, filters, time_grain)        
    return _evidence_chart_service.get(chart_id, interpretation, data)

@tool
def get_dataset_list() -> list[DatasetListItem]:
    """
    List all available Superset datasets.

    Use this tool when you need to identify which dataset contains the
    information required to answer the user's question.

    Returns a summary of each dataset including:
    - dataset ID
    - dataset name
    - optional business description
    - dataset type (physical or virtual)
    - underlying table or SQL definition
    """
    datasets = _dataset_list_service.get_dataset_list()
    return [dataset.model_dump() for dataset in datasets]

@tool
def get_dataset_detail(dataset_id: int) -> DatasetDetail:
    """
    Retrieve the complete metadata for a Superset dataset.

    Use this tool when you need detailed information about a dataset before
    querying or analyzing it.

    Returns:
    - available physical and calculated columns
    - reusable business metrics
    - existing charts built from the dataset
    - database connection information
    - dataset type and underlying table or SQL definition

    Existing metrics and calculated columns represent approved business logic
    and should be reused whenever they satisfy the user's request instead of
    recreating equivalent calculations.
    """
    detail = _dataset_detail_service.get(dataset_id)
    return detail.model_dump()


@tool
def execute_sql(
    db_connection_id: int,
    sql: str,
) -> dict:
    """
    Execute a read-only SQL query and return a small preview of the result.

    Use this tool for simple data retrieval tasks where only a small amount of
    data is needed to answer the user's question, such as:
    - Looking up values
    - Computing simple aggregates (SUM, COUNT, AVG, MIN, MAX)
    - Retrieving top-N records
    - Verifying query results
    - Inspecting a small subset of data

    This tool is intended for quick SQL exploration only. The result is limited
    to a small number of rows (currently 10) to reduce LLM context usage and
    improve response speed.

    Use this tool when a small preview of the query result is sufficient to
    answer the user's question directly.

    Do not use this tool when the complete query result will be required for
    subsequent analysis.

    Prefer reusing existing business metrics and calculated columns whenever
    possible instead of recreating equivalent SQL expressions.

    Args:
        db_connection_id: Superset database connection ID.
        sql: Read-only SQL statement to execute.

    Returns:
        Up to 10 rows from the query result for quick inspection and answering
        straightforward questions.
    """
    
    results = _sql_execution_service.execute_sql(
        db_connection_id,
        sql,
        query_limit=10
    )
    return results


@tool 
def execute_analytics_sql(
    db_connection_id: int,
    sql: str,
    query_limit: int = 5000,
    )->SQLExecutionResponse: 
    """
    Execute a read-only SQL query, store the complete result for subsequent
    analytics, and return an execution ID.

    Use this tool when the SQL result will be analyzed further rather than
    answered directly. Typical use cases include:
    - Time-series analysis
    - Cross-section analysis
    - Relationship analysis
    - Anomaly detection
    - Multi-step investigative workflows

    This tool stores the complete query result internally instead of returning
    all rows to the LLM. It returns:
    - An execution ID that can be passed to analytics tools.
    - A summary of the result schema.
    - A small sample of rows for inspection.
    - The analytics types supported by the result.

    Use the returned execution_id when calling analytics tools. Reuse the
    execution_id for subsequent analysis instead of executing the same SQL again,
    unless the query itself needs to change.

    Prefer reusing existing business metrics and calculated columns whenever
    possible instead of recreating equivalent SQL expressions.
    
    
    Args:
        db_connection_id: Superset database connection ID.
        sql: Read-only SQL statement to execute.
        query_limit: Maximum number of rows to store for analytics.

    Returns:
        SQLExecutionResponse containing:
        - execution_id
        - row_count
        - result columns
        - sample_rows
        - possible_analysis
    
    """
    result, data = _sql_execution_service.execute_sql_and_build_sample_data(
        database_id=db_connection_id,
        sql=sql,
        query_limit=query_limit
    ) 
    
    query_memory_service.save(
        execution_id=result.execution_id,
        data=data
    )
    
    return result.model_dump()
    
    
