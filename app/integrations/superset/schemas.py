"""Lightweight typing helpers for raw Superset API payloads."""

from __future__ import annotations

from typing import Any

# Superset responses are loosely typed JSON; keep aliases for clarity at the
# client/adapter boundary without over-modeling every Superset field.
type SupersetChartPayload = dict[str, Any]
type SupersetDatasetPayload = dict[str, Any]
type SupersetQueryObject = dict[str, Any]
type SupersetQueryContext = dict[str, Any]
