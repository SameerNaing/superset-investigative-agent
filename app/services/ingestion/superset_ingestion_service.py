"""Ingest Superset chart/dataset metadata into the canonical PostgreSQL model."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Analytic, Dataset, Provider
from app.db.repositories import (
    AnalyticRepository,
    DatasetRepository,
    DataSourceRepository,
)
from app.integrations.superset import SupersetAdapter, SupersetClient
from app.integrations.superset.time_grains import TimeGrainCatalog
from app.integrations.superset.types import data_type_from_coltype
from app.schemas.canonical import (
    CanonicalAnalytic,
    CanonicalDataset,
    CanonicalQueryColumn,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    analytic: Analytic
    dataset_source_id: str
    chart_source_id: str
    unsupported: list[dict[str, Any]]


class SupersetIngestionService:
    """
    Superset API -> Client -> Adapter -> Repositories -> PostgreSQL.

    Persistence is transactional: one commit per successful ingest_chart call.
    """

    def __init__(
        self,
        session: Session,
        *,
        client: SupersetClient | None = None,
        adapter: SupersetAdapter | None = None,
        data_source_name: str = "Superset",
    ) -> None:
        self._session = session
        self._client = client or SupersetClient()
        self._adapter = adapter or SupersetAdapter()
        self._data_sources = DataSourceRepository(session)
        self._datasets = DatasetRepository(session)
        self._analytics = AnalyticRepository(session)
        self._data_source_name = data_source_name

    def ingest_chart(self, chart_id: int) -> IngestionResult:
        data_source = self._data_sources.get_or_create(
            provider=Provider.SUPERSET,
            name=self._data_source_name,
        )

        chart = self._client.get_chart(chart_id)
        dataset_id = chart.get("datasource_id")
        if dataset_id is None:
            query_context = chart.get("query_context") or {}
            dataset_id = (query_context.get("datasource") or {}).get("id")
        if dataset_id is None:
            raise ValueError(f"Chart {chart_id} has no datasource_id")

        dataset_payload = self._client.get_dataset(int(dataset_id))
        canonical_dataset = self._adapter.to_dataset(dataset_payload)
        dataset = self._datasets.upsert_dataset_graph(
            data_source_id=data_source.id,
            canonical=canonical_dataset,
        )

        # Ensure ad-hoc metrics referenced by the chart exist before query links.
        time_grains = TimeGrainCatalog.from_records(
            (canonical_dataset.extra or {}).get("time_grains")
        )
        canonical_analytic = self._adapter.to_analytic(
            chart,
            dataset_source_id=str(dataset_id),
            time_grains=time_grains,
        )
        self._ensure_query_metrics(dataset, canonical_analytic)

        analytic = self._analytics.replace_analytic(
            dataset=dataset,
            canonical=canonical_analytic,
        )
        # Best-effort: resolve adhoc column dtypes via chart/data coltypes.
        self._refresh_adhoc_column_types(
            dataset_id=int(dataset_id),
            dataset=dataset,
            canonical_analytic=canonical_analytic,
        )
        self._session.commit()
        self._session.refresh(analytic)
        # Reload ordered query graph for callers.
        analytic = self._analytics.get_by_source_id(
            dataset.id,
            canonical_analytic.source_id,
        )
        assert analytic is not None

        return IngestionResult(
            analytic=analytic,
            dataset_source_id=canonical_dataset.source_id,
            chart_source_id=canonical_analytic.source_id,
            unsupported=canonical_analytic.unsupported,
        )

    def ingest_dataset(self, dataset_id: int) -> CanonicalDataset:
        data_source = self._data_sources.get_or_create(
            provider=Provider.SUPERSET,
            name=self._data_source_name,
        )
        payload = self._client.get_dataset(dataset_id)
        canonical = self._adapter.to_dataset(payload)
        self._datasets.upsert_dataset_graph(
            data_source_id=data_source.id,
            canonical=canonical,
        )
        self._session.commit()
        return canonical

    def _ensure_query_metrics(
        self,
        dataset: Dataset,
        canonical_analytic: CanonicalAnalytic,
    ) -> None:
        for query in canonical_analytic.queries:
            for metric_ref in query.metrics:
                existing = None
                if metric_ref.source_id is not None:
                    existing = self._datasets.find_metric(
                        dataset,
                        source_id=metric_ref.source_id,
                    )
                if existing is None:
                    existing = self._datasets.find_metric(
                        dataset,
                        name=metric_ref.metric_name,
                        expression=metric_ref.expression,
                    )
                if existing is not None:
                    continue
                # Adhoc metrics only: create when an expression is present.
                if metric_ref.expression is None:
                    continue
                self._datasets.ensure_metric(
                    dataset,
                    name=metric_ref.metric_name,
                    expression=metric_ref.expression,
                    source_id=metric_ref.source_id,
                )

    def _collect_adhoc_columns(
        self,
        canonical_analytic: CanonicalAnalytic,
    ) -> list[CanonicalQueryColumn]:
        """Unique chart adhoc columns (label + sqlExpression)."""
        collected: list[CanonicalQueryColumn] = []
        seen: set[tuple[str, str]] = set()
        for query in canonical_analytic.queries:
            for col in query.columns:
                if not col.expression:
                    continue
                key = (col.column_name, col.expression)
                if key in seen:
                    continue
                seen.add(key)
                collected.append(col)
        return collected

    def _refresh_adhoc_column_types(
        self,
        *,
        dataset_id: int,
        dataset: Dataset,
        canonical_analytic: CanonicalAnalytic,
    ) -> None:
        """
        Infer dtypes for Explore adhoc columns via POST /api/v1/chart/data.

        Superset has no dedicated type API for adhoc sqlExpression columns; the
        chart data response includes colnames + coltypes (GenericDataType ints).
        Failures are ignored so ingestion still succeeds with UNKNOWN.
        """
        adhoc_columns = self._collect_adhoc_columns(canonical_analytic)
        if not adhoc_columns:
            return

        probe = {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [
                {
                    "columns": [
                        {
                            "expressionType": "SQL",
                            "label": col.column_name,
                            "sqlExpression": col.expression,
                        }
                        for col in adhoc_columns
                    ],
                    "metrics": [],
                    "row_limit": 1,
                }
            ],
            "result_type": "results",
        }

        try:
            results = self._client.get_chart_data(probe)
        except Exception:
            logger.warning(
                "adhoc column type probe failed for dataset_id=%s",
                dataset_id,
                exc_info=True,
            )
            return

        if not results:
            return

        coltypes = results[0].get("coltypes") or []
        # Prefer index alignment with the probe column list over colnames,
        # which can be rewritten by post-processing / aliases.
        for index, adhoc in enumerate(adhoc_columns):
            if index >= len(coltypes):
                break
            data_type = data_type_from_coltype(coltypes[index])
            if not data_type:
                continue
            column = self._datasets.find_column(
                dataset,
                name=adhoc.column_name,
                expression=adhoc.expression,
            )
            if column is None:
                continue
            column.data_type = data_type
            if data_type == "TEMPORAL":
                column.is_temporal = True

        self._session.flush()
