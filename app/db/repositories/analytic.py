from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Analytic,
    Dataset,
    Query,
    QueryColumn,
    QueryFilter,
    QueryMetric,
    QueryOrder,
    Visualization,
)
from app.db.models.query import FilterType
from app.db.repositories.dataset import DatasetRepository
from app.schemas.canonical import (
    CanonicalAnalytic,
    CanonicalQuery,
    CanonicalVisualization,
)


class AnalyticRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._datasets = DatasetRepository(session)

    def get_by_source_id(
        self,
        dataset_id: uuid.UUID,
        source_id: str,
        *,
        load_graph: bool = True,
    ) -> Analytic | None:
        stmt = select(Analytic).where(
            Analytic.dataset_id == dataset_id,
            Analytic.source_id == source_id,
        )
        if load_graph:
            stmt = stmt.options(
                selectinload(Analytic.queries).selectinload(Query.columns),
                selectinload(Analytic.queries).selectinload(Query.metrics),
                selectinload(Analytic.queries).selectinload(Query.filters),
                selectinload(Analytic.queries).selectinload(Query.orders),
                selectinload(Analytic.visualizations),
            )
        return self._session.scalar(stmt)

    def replace_analytic(
        self,
        *,
        dataset: Dataset,
        canonical: CanonicalAnalytic,
    ) -> Analytic:
        # Lightweight lookup: children are cleared/replaced immediately.
        analytic = self.get_by_source_id(
            dataset.id,
            canonical.source_id,
            load_graph=False,
        )
        if analytic is None:
            analytic = Analytic(
                dataset_id=dataset.id,
                source_id=canonical.source_id,
                name=canonical.name,
                description=canonical.description,
                verified=False,
            )
            self._session.add(analytic)
            self._session.flush()
        else:
            analytic.name = canonical.name
            analytic.description = canonical.description
            self._clear_query_graph(analytic)
            self._clear_visualizations(analytic)

        for query in canonical.queries:
            self._create_query(analytic, dataset, query)

        if canonical.visualization is not None:
            self._create_visualization(analytic, canonical.visualization)

        self._session.flush()
        return analytic

    def _clear_query_graph(self, analytic: Analytic) -> None:
        query_ids = [
            row[0]
            for row in self._session.execute(
                select(Query.id).where(Query.analytic_id == analytic.id)
            )
        ]
        if not query_ids:
            return

        self._session.execute(
            delete(QueryColumn).where(QueryColumn.query_id.in_(query_ids))
        )
        self._session.execute(
            delete(QueryMetric).where(QueryMetric.query_id.in_(query_ids))
        )
        self._session.execute(
            delete(QueryFilter).where(QueryFilter.query_id.in_(query_ids))
        )
        self._session.execute(
            delete(QueryOrder).where(QueryOrder.query_id.in_(query_ids))
        )
        self._session.execute(delete(Query).where(Query.id.in_(query_ids)))
        self._session.flush()

    def _clear_visualizations(self, analytic: Analytic) -> None:
        self._session.execute(
            delete(Visualization).where(Visualization.analytic_id == analytic.id)
        )
        self._session.flush()

    def _create_query(
        self,
        analytic: Analytic,
        dataset: Dataset,
        canonical: CanonicalQuery,
    ) -> Query:
        query = Query(
            analytic_id=analytic.id,
            position=canonical.position,
            row_limit=canonical.row_limit,
        )
        self._session.add(query)
        self._session.flush()

        for col in canonical.columns:
            # Physical columns are registered on the dataset; Superset adhoc
            # columns (label + sqlExpression) are matched/created by
            # (name, expression) so a shared label with different SQL is kept.
            column = self._datasets.find_column(
                dataset,
                name=col.column_name,
                expression=col.expression,
            )
            if column is None:
                column = self._datasets.ensure_column(
                    dataset,
                    name=col.column_name,
                    data_type="UNKNOWN",
                    is_temporal=col.time_grain is not None,
                    expression=col.expression,
                )
            self._session.add(
                QueryColumn(
                    query_id=query.id,
                    column_id=column.id,
                    time_grain=col.time_grain,
                )
            )

        for metric_ref in canonical.metrics:
            metric = None

            if metric_ref.source_id is not None:
                metric = self._datasets.find_metric(
                    dataset,
                    source_id=metric_ref.source_id,
                )

            if metric is None:
                metric = self._datasets.find_metric(
                    dataset,
                    name=metric_ref.metric_name,
                    expression=metric_ref.expression,
                )

            # Saved metrics resolve above; adhoc (or missing) metrics are created.
            if metric is None:
                expression = metric_ref.expression or metric_ref.metric_name
                metric = self._datasets.ensure_metric(
                    dataset,
                    name=metric_ref.metric_name,
                    expression=expression,
                    source_id=metric_ref.source_id,
                )

            self._session.add(QueryMetric(query_id=query.id, metric_id=metric.id))

        for filt in canonical.filters:
            column_id = None
            metric_id = None

            if filt.column_name:
                column = self._datasets.find_column(
                    dataset,
                    name=filt.column_name,
                    expression=filt.expression,
                )
                if column is None:
                    column = self._datasets.ensure_column(
                        dataset,
                        name=filt.column_name,
                        data_type="UNKNOWN",
                        expression=filt.expression,
                    )
                column_id = column.id

            if filt.metric_name:
                metric = self._datasets.find_metric(
                    dataset,
                    name=filt.metric_name,
                    expression=filt.expression,
                )
                if metric is None:
                    metric = self._datasets.ensure_metric(
                        dataset,
                        name=filt.metric_name,
                        expression=filt.expression or filt.metric_name,
                    )
                metric_id = metric.id

            # Expression filters may intentionally have neither column nor metric.
            if (
                filt.filter_type != FilterType.EXPRESSION
                and column_id is None
                and metric_id is None
            ):
                raise ValueError(
                    f"Structured query filter has no resolvable column or metric "
                    f"target in dataset {dataset.id}"
                )

            self._session.add(
                QueryFilter(
                    query_id=query.id,
                    clause=filt.clause,
                    filter_type=filt.filter_type,
                    operator=filt.operator,
                    value=filt.value,
                    expression=filt.expression,
                    column_id=column_id,
                    metric_id=metric_id,
                )
            )

        for order in canonical.orders:
            column_id = None
            metric_id = None

            # Match Superset resolution: metric label/name, then column.
            if order.metric_name:
                metric = self._datasets.find_metric(
                    dataset,
                    name=order.metric_name,
                    expression=order.expression,
                )
                if metric is not None:
                    metric_id = metric.id

            if metric_id is None and order.column_name:
                column = self._datasets.find_column(
                    dataset,
                    name=order.column_name,
                    expression=order.expression,
                )
                if column is not None:
                    column_id = column.id

            if column_id is None and metric_id is None:
                # Chart may order by an adhoc metric/column not yet registered.
                if order.expression and order.metric_name:
                    metric = self._datasets.ensure_metric(
                        dataset,
                        name=order.metric_name,
                        expression=order.expression,
                    )
                    metric_id = metric.id
                elif order.column_name:
                    column = self._datasets.ensure_column(
                        dataset,
                        name=order.column_name,
                        data_type="UNKNOWN",
                        expression=order.expression,
                    )
                    column_id = column.id
                elif order.metric_name:
                    metric = self._datasets.ensure_metric(
                        dataset,
                        name=order.metric_name,
                        expression=order.expression or order.metric_name,
                    )
                    metric_id = metric.id

            if column_id is None and metric_id is None:
                raise ValueError(
                    f"Query order references unknown target "
                    f"column={order.column_name!r}, "
                    f"metric={order.metric_name!r} "
                    f"in dataset {dataset.id}"
                )

            self._session.add(
                QueryOrder(
                    query_id=query.id,
                    column_id=column_id,
                    metric_id=metric_id,
                    asc=order.asc,
                    position=order.position,
                )
            )

        self._session.flush()
        return query

    def _create_visualization(
        self,
        analytic: Analytic,
        canonical: CanonicalVisualization,
    ) -> Visualization:
        visualization = Visualization(
            analytic_id=analytic.id,
            source_id=canonical.source_id,
            name=canonical.name,
            description=canonical.description,
            viz_type=canonical.viz_type,
            verified=False,
            options=canonical.options,
        )
        self._session.add(visualization)
        self._session.flush()
        return visualization
