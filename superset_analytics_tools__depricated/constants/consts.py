from enum import Enum
class QueryType(str, Enum): 
    QUERY_A = "query_a"
    QUERY_B = "query_b"
    
class ChartMark(str, Enum):
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"