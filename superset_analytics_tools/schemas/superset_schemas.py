from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class Metric(BaseModel):
    label: str = Field(
        ...,
        description=(
            "The business-friendly metric name. Always check existing metrics "
            "before creating a new calculation."
        ),
    )

    sql_expression: Optional[str] = Field(
        None,
        description=(
            "The SQL expression defining this metric. If present, reuse this "
            "expression instead of generating a new one."
        ),
    )

    column_name: Optional[str] = Field(
        None,
        description=(
            "The source column used by this metric when it is a simple aggregation. "
        ),
    )

    aggregate: Optional[str] = Field(
        None,
        description=(
            "Aggregation function applied to the column, such as COUNT, SUM, AVG, "
            "MIN or MAX. If both aggregate and column_name are present, they define "
            "the metric calculation."
        ),
    )  

class Operator(str, Enum):
    EQ = "=="
    NEQ = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    ILIKE = "ILIKE"
    NOT_ILIKE = "NOT ILIKE"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    IN = "IN"
    NOT_IN = "NOT IN"
    TEMPORAL_RANGE = "TEMPORAL_RANGE"

class Analytics(str, Enum): 
    TIME_SERIES = 'Timeseries'
    CROSS_SECTION = "Cross Section"
    RELATIONAL = "Relational"

class LockedFilters(BaseModel):
    sql : str 
    # WHERE, HAVING
    clause: str
    
class DataProfile(BaseModel): 
    numeric_cols: List[str] 
    categorial_cols: List[str] 
    time_col: str | None = None
    possible_analysis : Optional[List[Analytics]] = None

class SampleData(BaseModel): 
    dataProfile : DataProfile
    samples: List

class AvailableFilter(BaseModel):
    col: str = Field(
        description=(
            "The dataset column that can be used as a filter when querying or "
            "modifying the chart."
        )
    )

    dtype: str = Field(
        description=(
            "The data type of the filter column (for example STRING, TEXT, "
            "INTEGER, FLOAT, BOOLEAN, DATE, or TIMESTAMP). Use this to determine "
            "the appropriate filter operator and value format."
        )
    )

    available_values: Optional[List[Optional[str]]] = Field(
        default=None,
        description=(
            "Known values for this filter column. This field is only populated for "
            "STRING or TEXT columns and contains the distinct values available in "
            "the dataset that can be used for filtering. Null for non-text columns."
        )
    )


class AppliedFilter(BaseModel): 
    col : str 
    op: Operator
    val: str | List[str | int] | int | None = None


class TimeGrainInfo(BaseModel):
    col: str = Field(
        description="The datetime column currently used for time aggregation on the chart. Changing the time grain will aggregate this column into larger or smaller time buckets."
    )

    current_val: str | None = Field(
        default=None,
        description="The currently applied time grain (e.g. PT1H, P1D, P1W). This is the chart's current aggregation level."
    )

    available_vals: dict[str, str] = Field(
        default_factory=dict,
        description="The time grains supported by this chart. Keys are user-friendly names (e.g. Hour, Day, Month) and values are the Superset time grain codes to use when updating the chart."
    )

class Dimension(BaseModel):
    name: str = Field(
        description=(
            "The logical name of the dimension. For a regular dataset column, this is "
            "the column name. For a SQL-based dimension, this is the display label "
            "assigned by the chart author. Use this field when referring to, selecting, "
            "or modifying the chart's dimensions."
        )
    )

    sql_expression: str | None = Field(
        default=None,
        description=(
            "The SQL expression used to compute the dimension when the dimension is "
            "based on a custom SQL expression. This field is null for regular dataset "
            "columns."
        )
    )
class ChartDetail(BaseModel):
    id: int
    name: str
    viz_type: str

    metrics: List[Metric] | List[List[Metric]]
    
    dimensions: List[Dimension] | List[List[Dimension]] = Field(
        default=[],
        description=(
            "Categorical dimensions currently used by the chart to group or break down "
            "the displayed metrics. These are the user-selected grouping fields and do "
            "not include the time axis. Empty if the chart has no categorical dimensions."
        )
    )
    
    timegrain: TimeGrainInfo | None = Field(
    default=None,
    description=(
        "Time aggregation settings for the chart. "
        "This field is only present when the chart's x-axis or table or pivot table column is a datetime column. "
        "Use it when the user or you want to change the aggregation level, such as Hour, Day, Week, Month, or Year. "
        "If this field is null, the chart does not support time-grain adjustments."
        ),
    )
    
    available_filters : List[AvailableFilter]
    
    applied_filters : List[AppliedFilter] | List[List[AppliedFilter]] | None = None
    locked_filters: List[LockedFilters] | List[List[LockedFilters]] | None = None
    
    data_samples : SampleData | List[SampleData] = []
    
    
class ChartList(BaseModel):
    id: int = Field(..., description="The unique Superset chart ID.")
    viz_type : str = Field(
        ...,
        description="The type of visualization used for this chart."
    )

    name: str = Field(
        ...,
        description="The human-readable name of the chart."
    )
    
    
class DatasetListItem(BaseModel):
    id: int = Field(..., description="The unique Superset dataset ID.")

    name: str = Field(
        ...,
        description="The human-readable name of the dataset."
    )

    description: str | None = Field(
        None,
        description="Optional business description of what this dataset represents."
    )

    kind: str = Field(
        ...,
        description="The dataset type. Usually either 'physical' or 'virtual'."
    )

    table: str = Field(
        ...,
        description=(
            "For physical datasets this is schema.table, for example "
            "'product.report_data'. For virtual datasets this may be the approved "
            "SQL query or function that defines the dataset."
        ),
    )

class DatasetColumn(BaseModel):
    name: str = Field(
        ...,
        description="Column name."
    )

    type: str = Field(
        ...,
        description="Column data type."
    )

    description: Optional[str] = Field(
        None,
        description="Optional business description."
    )

    is_calculated: bool = Field(
        ...,
        description=(
            "True if this is a calculated column defined in Superset. "
            "False if it is a physical column from the underlying table."
        ),
    )

    expression: Optional[str] = Field(
        None,
        description=(
             "SQL expression for calculated columns. "
             "Calculated columns do not physically exist in the underlying database. "
             "When generating raw SQL, substitute the column with this expression."
        ),
    )

    filterable: bool = Field(
        ...,
        description="Whether this column can be used in filters."
    )

    groupby: bool = Field(
        ...,
        description="Whether this column can be used in GROUP BY."
    )

    is_time: bool = Field(
        ...,
        description="Whether this is a datetime column."
    )

class DatasetDetail(BaseModel):
    id: int = Field(..., description="The unique Superset dataset ID.")

    table: str = Field(
        ...,
        description=(
            "For physical datasets this is schema.table, for example "
            "'product.report_data'. For virtual datasets this contains the approved "
            "SQL query or function defining the dataset. Never modify or rewrite "
            "the SQL of a virtual dataset; treat it as business logic."
        ),
    )

    columns: list[DatasetColumn] = Field(
        ...,
        description=(
            "Available columns that can be used for SQL selection, filtering, "
            "grouping, ordering, and metric calculations."
        ),
    )

    db_connection_id: int = Field(
        ...,
        description="The Superset database connection ID used for SQL execution."
    )

    charts: list[ChartList] = Field(
        ...,
        description=(
            "Existing Superset charts built from this dataset. Use these as references "
            "for reusable visualizations, verified groupings, and existing metric usage."
        ),
    )

    metrics: list[Metric] = Field(
        ...,
        description=(
            "Business metrics already defined for this dataset. Always reuse these "
            "metrics when they match the user's request instead of inventing a new calculation."
        ),
    )

    kind: str = Field(
        ...,
        description="The dataset type. Usually either 'physical' or 'virtual'."
    )
