"""Resolve Superset time grains from the live instance catalog.

There is no dedicated time-grain REST endpoint. Grains are engine-specific and
include ``TIME_GRAIN_ADDONS`` from ``superset/config.py``. The live catalog is
``GET /api/v1/dataset/{id}`` → ``time_grain_sqla``: ``[[duration, label], ...]``,
built from ``database.grains()`` (see ``SqlaTable.time_grain_sqla``).

Chart payloads store the duration/key (``PT1H``, or a custom addon like
``SHIFT_AM``). Canonical ``time_grain`` is the slug of that instance's label so
custom grains (shifts, fiscal periods, …) are first-class without a hardcoded map.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_grain_label(label: str) -> str:
    slug = _SLUG_RE.sub("_", label.strip().lower()).strip("_")
    return slug or label.strip()


@dataclass(frozen=True)
class TimeGrainInfo:
    """One grain as advertised by a Superset database engine."""

    duration: str  # instance key stored on charts (ISO duration or addon id)
    label: str  # untranslated config label ("Hour", "Morning Shift")
    name: str  # canonical slug ("hour", "morning_shift")


class TimeGrainCatalog:
    """Duration/label catalog for one Superset database (via its dataset)."""

    def __init__(self, grains: Sequence[TimeGrainInfo] = ()) -> None:
        self._grains: tuple[TimeGrainInfo, ...] = tuple(grains)
        self._by_duration = {grain.duration: grain for grain in self._grains}
        self._by_name = {grain.name: grain for grain in self._grains}

    def __bool__(self) -> bool:
        return bool(self._grains)

    def __iter__(self) -> Iterator[TimeGrainInfo]:
        return iter(self._grains)

    @classmethod
    def from_time_grain_sqla(cls, raw: Any) -> TimeGrainCatalog:
        """Parse dataset API ``time_grain_sqla`` (list of ``[duration, label]``)."""
        grains: list[TimeGrainInfo] = []
        seen: set[str] = set()
        for duration, label in _iter_duration_label_pairs(raw):
            if duration in seen:
                continue
            seen.add(duration)
            grains.append(
                TimeGrainInfo(
                    duration=duration,
                    label=label,
                    name=slugify_grain_label(label),
                )
            )
        return cls(grains)

    @classmethod
    def from_records(
        cls,
        records: Sequence[dict[str, Any]] | None,
    ) -> TimeGrainCatalog:
        """Rebuild from ``CanonicalDataset.extra['time_grains']``."""
        if not records:
            return cls()
        grains: list[TimeGrainInfo] = []
        for record in records:
            duration = record.get("duration")
            if not duration:
                continue
            label = str(record.get("label") or duration)
            name = str(record.get("name") or slugify_grain_label(label))
            grains.append(TimeGrainInfo(duration=str(duration), label=label, name=name))
        return cls(grains)

    def to_records(self) -> list[dict[str, str]]:
        return [
            {"duration": grain.duration, "label": grain.label, "name": grain.name}
            for grain in self._grains
        ]

    def resolve(self, value: str) -> str:
        """Map a chart grain value to the canonical slug, or keep it as-is."""
        if value in self._by_duration:
            return self._by_duration[value].name
        lowered = value.lower()
        if lowered in self._by_name:
            return lowered
        for grain in self._grains:
            if grain.label.lower() == lowered:
                return grain.name
        return value

    def duration_for_name(self, name: str) -> str | None:
        grain = self._by_name.get(name) or self._by_duration.get(name)
        if grain is None:
            return None
        return grain.duration


def _iter_duration_label_pairs(raw: Any) -> Iterable[tuple[str, str]]:
    if not raw:
        return
    if isinstance(raw, dict):
        items: Iterable[Any] = raw.items()
    elif isinstance(raw, (list, tuple)):
        items = raw
    else:
        return

    for item in items:
        duration: Any
        label: Any
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            duration, label = item[0], item[1]
        elif isinstance(item, dict):
            duration = item.get("duration") or item.get("name")
            label = item.get("label") or item.get("name") or duration
        else:
            continue
        if duration is None:
            continue
        duration_text = str(duration).strip()
        if not duration_text:
            continue
        label_text = str(label).strip() if label is not None else duration_text
        yield duration_text, label_text or duration_text


def normalize_time_grain(
    value: str | None,
    catalog: TimeGrainCatalog | None = None,
) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if catalog:
        return catalog.resolve(text)
    return text
