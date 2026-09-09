"""Map Superset GenericDataType codes to canonical data_type strings."""

from __future__ import annotations

# Mirrors superset.utils.core.GenericDataType
SUPERSET_COLTYPE_TO_DATA_TYPE: dict[int, str] = {
    0: "NUMERIC",
    1: "STRING",
    2: "TEMPORAL",
    3: "BOOLEAN",
}


def data_type_from_coltype(coltype: int | None) -> str | None:
    if coltype is None:
        return None
    return SUPERSET_COLTYPE_TO_DATA_TYPE.get(int(coltype))
