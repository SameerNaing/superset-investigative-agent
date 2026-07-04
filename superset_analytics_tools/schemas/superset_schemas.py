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
    col: str 
    dtype: str 
    available_values: Optional[List[Optional[str]]] = None


class AppliedFilter(BaseModel): 
    col : str 
    op: Operator
    val: str | List[str | int] | int | None = None


class ChartDetail(BaseModel):
    id: int
    name: str
    viz_type: str

    metrics: List[Metric] | List[List[Metric]]
    
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
