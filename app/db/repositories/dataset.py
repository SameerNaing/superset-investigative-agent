from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Dataset, DatasetColumn, Metric
from app.schemas.canonical import (
    CanonicalDataset,
    CanonicalDatasetColumn,
    CanonicalMetric,
)


def _normalize_expression(expression: str | None) -> str | None:
    if expression is None:
        return None
    text = expression.strip()
    return text or None


def _expressions_equal(left: str | None, right: str | None) -> bool:
    return _normalize_expression(left) == _normalize_expression(right)


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_source_id(
        self,
        data_source_id: uuid.UUID,
        source_id: str,
    ) -> Dataset | None:
        return self._session.scalar(
            select(Dataset)
            .where(
                Dataset.data_source_id == data_source_id,
                Dataset.source_id == source_id,
            )
            .options(
                selectinload(Dataset.columns),
                selectinload(Dataset.metrics),
            )
        )

    def upsert_dataset_graph(
        self,
        *,
        data_source_id: uuid.UUID,
        canonical: CanonicalDataset,
    ) -> Dataset:
        dataset = self.get_by_source_id(data_source_id, canonical.source_id)
        if dataset is None:
            dataset = Dataset(
                data_source_id=data_source_id,
                source_id=canonical.source_id,
                name=canonical.name,
                description=canonical.description,
                verified=False,
                extra=canonical.extra,
            )
            self._session.add(dataset)
            self._session.flush()
        else:
            dataset.name = canonical.name
            dataset.description = canonical.description
            dataset.extra = canonical.extra

        columns_by_source = {
            col.source_id: col for col in dataset.columns if col.source_id
        }
        columns_by_name_expr = {
            (col.name, _normalize_expression(col.expression)): col
            for col in dataset.columns
        }

        for col in canonical.columns:
            self._upsert_column(dataset, col, columns_by_source, columns_by_name_expr)

        metrics_by_source = {
            metric.source_id: metric for metric in dataset.metrics if metric.source_id
        }
        metrics_by_name_expr = {
            (metric.name, _normalize_expression(metric.expression)): metric
            for metric in dataset.metrics
        }

        for metric in canonical.metrics:
            self._upsert_metric(
                dataset,
                metric,
                metrics_by_source,
                metrics_by_name_expr,
            )

        self._session.flush()
        return dataset

    def ensure_metric(
        self,
        dataset: Dataset,
        *,
        name: str,
        expression: str,
        source_id: str | None = None,
        description: str | None = None,
    ) -> Metric:
        expression = _normalize_expression(expression) or expression

        if source_id:
            metric = self.find_metric(dataset, source_id=source_id)
            if metric is not None:
                metric.name = name
                metric.expression = expression
                if description is not None:
                    metric.description = description
                return metric

        metric = self.find_metric(dataset, name=name, expression=expression)
        if metric is not None:
            if source_id and not metric.source_id:
                metric.source_id = source_id
            return metric

        metric = Metric(
            dataset_id=dataset.id,
            source_id=source_id,
            name=name,
            description=description,
            verified=False,
            expression=expression,
        )
        self._session.add(metric)
        dataset.metrics.append(metric)
        self._session.flush()
        return metric

    def ensure_column(
        self,
        dataset: Dataset,
        *,
        name: str,
        data_type: str = "UNKNOWN",
        is_temporal: bool = False,
        expression: str | None = None,
        source_id: str | None = None,
        description: str | None = None,
    ) -> DatasetColumn:
        expression = _normalize_expression(expression)
        existing = self.find_column(
            dataset,
            name=name,
            expression=expression,
            source_id=source_id,
        )
        if existing is not None:
            return existing

        columns_by_source = {
            col.source_id: col for col in dataset.columns if col.source_id
        }
        columns_by_name_expr = {
            (col.name, _normalize_expression(col.expression)): col
            for col in dataset.columns
        }
        return self._upsert_column(
            dataset,
            CanonicalDatasetColumn(
                source_id=source_id,
                name=name,
                description=description,
                data_type=data_type,
                is_temporal=is_temporal,
                expression=expression,
            ),
            columns_by_source,
            columns_by_name_expr,
        )

    def find_column(
        self,
        dataset: Dataset,
        *,
        name: str | None = None,
        expression: str | None = None,
        source_id: str | None = None,
    ) -> DatasetColumn | None:
        if source_id:
            for col in dataset.columns:
                if col.source_id == source_id:
                    return col

        if name is None:
            return None

        normalized = _normalize_expression(expression)

        # Adhoc / calculated: identity is (name, expression).
        if normalized is not None:
            for col in dataset.columns:
                if col.name == name and _expressions_equal(col.expression, normalized):
                    return col
            return None

        # Physical / name-only reference: match name with no expression.
        for col in dataset.columns:
            if col.name == name and _normalize_expression(col.expression) is None:
                return col
        return None

    def find_metric(
        self,
        dataset: Dataset,
        *,
        name: str | None = None,
        expression: str | None = None,
        source_id: str | None = None,
    ) -> Metric | None:
        if source_id:
            for metric in dataset.metrics:
                if metric.source_id == source_id:
                    return metric

        if name is None:
            return None

        normalized = _normalize_expression(expression)

        # Adhoc or exact saved metric: require name + expression.
        if normalized is not None:
            for metric in dataset.metrics:
                if metric.name == name and _expressions_equal(
                    metric.expression, normalized
                ):
                    return metric
            return None

        # Name-only (saved metric string ref in query_context): match by name.
        for metric in dataset.metrics:
            if metric.name == name:
                return metric
        return None

    def _upsert_column(
        self,
        dataset: Dataset,
        canonical: CanonicalDatasetColumn,
        by_source: dict[str, DatasetColumn],
        by_name_expr: dict[tuple[str, str | None], DatasetColumn],
    ) -> DatasetColumn:
        expression = _normalize_expression(canonical.expression)
        existing = None
        if canonical.source_id and canonical.source_id in by_source:
            existing = by_source[canonical.source_id]
        elif (canonical.name, expression) in by_name_expr:
            existing = by_name_expr[(canonical.name, expression)]

        if existing is None:
            column = DatasetColumn(
                dataset_id=dataset.id,
                source_id=canonical.source_id,
                name=canonical.name,
                description=canonical.description,
                verified=False,
                data_type=canonical.data_type,
                is_temporal=canonical.is_temporal,
                expression=expression,
            )
            self._session.add(column)
            dataset.columns.append(column)
            if canonical.source_id:
                by_source[canonical.source_id] = column
            by_name_expr[(canonical.name, expression)] = column
            self._session.flush()
            return column

        existing.name = canonical.name
        existing.description = canonical.description
        existing.data_type = canonical.data_type
        existing.is_temporal = canonical.is_temporal
        existing.expression = expression
        if canonical.source_id and not existing.source_id:
            existing.source_id = canonical.source_id
        return existing

    def _upsert_metric(
        self,
        dataset: Dataset,
        canonical: CanonicalMetric,
        by_source: dict[str, Metric],
        by_name_expr: dict[tuple[str, str | None], Metric],
    ) -> Metric:
        expression = _normalize_expression(canonical.expression) or canonical.expression
        existing = None
        if canonical.source_id and canonical.source_id in by_source:
            existing = by_source[canonical.source_id]
        elif (canonical.name, _normalize_expression(expression)) in by_name_expr:
            existing = by_name_expr[(canonical.name, _normalize_expression(expression))]

        if existing is None:
            metric = Metric(
                dataset_id=dataset.id,
                source_id=canonical.source_id,
                name=canonical.name,
                description=canonical.description,
                verified=False,
                expression=expression,
            )
            self._session.add(metric)
            dataset.metrics.append(metric)
            if canonical.source_id:
                by_source[canonical.source_id] = metric
            by_name_expr[(canonical.name, _normalize_expression(expression))] = metric
            return metric

        existing.name = canonical.name
        existing.description = canonical.description
        existing.expression = expression
        if canonical.source_id and not existing.source_id:
            existing.source_id = canonical.source_id
        return existing
