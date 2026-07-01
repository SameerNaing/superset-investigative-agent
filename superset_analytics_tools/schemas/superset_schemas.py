from enum import Enum
from typing import Any, Optional, List
from uuid import UUID
from pydantic import BaseModel


class Metric(BaseModel):
    label: str
    sql_expression: Optional[str] = None
    column_name: Optional[str] = None
    aggregate: Optional[str] = None
    

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
    id: int
    viz_type : str 
    name: str