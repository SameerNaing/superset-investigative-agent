from ..constants import superset_consts
from ..schemas import superset_schemas

def get_possible_analysis(time_cols:list[str], numerical_cols:list[str], categorical_cols:list[str]):
    possible_analysis = []
    
    if time_cols and numerical_cols:
        possible_analysis.append(superset_schemas.Analytics.TIME_SERIES)
    if categorical_cols and numerical_cols:
        possible_analysis.append(superset_schemas.Analytics.CROSS_SECTION)
    if len(numerical_cols) > 1:
        possible_analysis.append(superset_schemas.Analytics.RELATIONAL)
        
    return possible_analysis


def build_sample_data(table_result, form_data, viz_type, include_possible_analysis=True):
    cols = table_result.get("colnames", [])
    cols_types = table_result.get("coltypes", [])
    data = table_result.get("data", [])[:3]

    def cols_by_dtype(dtype):
        return [cols[i] for i, col_type in enumerate(cols_types) if col_type == dtype]

    time_cols = cols_by_dtype(superset_consts.DTypeMapping.TEMPORAL)
    categorical_cols = cols_by_dtype(superset_consts.DTypeMapping.STRING)
    numerical_cols = [col for col in cols_by_dtype(superset_consts.DTypeMapping.NUMERIC) if not col.endswith("_sort")]

    chart_time_column = None
    if viz_type == superset_consts.VizType.GANTT:
        chart_time_column = form_data.get("start_time")
    else:
        x_axis = form_data.get("x_axis")
        if x_axis in time_cols:
            chart_time_column = x_axis

    possible_analysis = get_possible_analysis(chart_time_column, numerical_cols, categorical_cols)

    profile = superset_schemas.DataProfile(
        numeric_cols=numerical_cols,
        categorial_cols=categorical_cols,
        time_col=chart_time_column,
        possible_analysis=possible_analysis if include_possible_analysis else None,
    )
    return superset_schemas.SampleData(dataProfile=profile, samples=data)
