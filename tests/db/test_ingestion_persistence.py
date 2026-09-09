"""Repository/ingestion persistence tests against the configured PostgreSQL DB."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db.models import Analytic, Dataset, Provider, Query
from app.db.models.query import FilterClause, FilterOperator, FilterType
from app.db.models.visualization import VizType
from app.db.repositories import (
    AnalyticRepository,
    DatasetRepository,
    DataSourceRepository,
)
from app.db.session import get_session_factory
from app.schemas.canonical import (
    CanonicalAnalytic,
    CanonicalDataset,
    CanonicalDatasetColumn,
    CanonicalMetric,
    CanonicalQuery,
    CanonicalQueryColumn,
    CanonicalQueryFilter,
    CanonicalQueryMetric,
    CanonicalQueryOrder,
    CanonicalVisualization,
)


@pytest.fixture
def session():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


def test_upsert_dataset_and_analytic_idempotent(session):
    suffix = uuid.uuid4().hex[:8]
    dataset_source_id = f"ds-{suffix}"
    chart_source_id = f"chart-{suffix}"

    data_sources = DataSourceRepository(session)
    datasets = DatasetRepository(session)
    analytics = AnalyticRepository(session)

    data_source = data_sources.get_or_create(
        provider=Provider.SUPERSET,
        name="Superset",
    )
    canonical_dataset = CanonicalDataset(
        source_id=dataset_source_id,
        name=f"dataset_{suffix}",
        description="test",
        columns=[
            CanonicalDatasetColumn(
                source_id=f"c1-{suffix}",
                name="material_type",
                data_type="STRING",
            ),
            CanonicalDatasetColumn(
                source_id=f"c2-{suffix}",
                name="event_time",
                data_type="TIMESTAMP",
                is_temporal=True,
            ),
        ],
        metrics=[
            CanonicalMetric(
                source_id=f"m1-{suffix}",
                name="Production BCM",
                expression="SUM(bcm)",
            )
        ],
    )
    dataset = datasets.upsert_dataset_graph(
        data_source_id=data_source.id,
        canonical=canonical_dataset,
    )
    session.flush()

    analytic_payload = CanonicalAnalytic(
        source_id=chart_source_id,
        name=f"analytic_{suffix}",
        description="demo",
        dataset_source_id=dataset_source_id,
        queries=[
            CanonicalQuery(
                position=0,
                row_limit=100,
                columns=[
                    CanonicalQueryColumn(column_name="event_time", time_grain="day"),
                    CanonicalQueryColumn(column_name="material_type"),
                ],
                metrics=[
                    CanonicalQueryMetric(
                        metric_name="Production BCM",
                        expression="SUM(bcm)",
                        source_id=f"m1-{suffix}",
                    )
                ],
                filters=[
                    CanonicalQueryFilter(
                        clause=FilterClause.WHERE,
                        filter_type=FilterType.STRUCTURED,
                        operator=FilterOperator.EQ,
                        value="ORE",
                        column_name="material_type",
                    )
                ],
                orders=[
                    CanonicalQueryOrder(
                        metric_name="Production BCM",
                        asc=False,
                        position=0,
                    )
                ],
            ),
            CanonicalQuery(
                position=1,
                row_limit=100,
                columns=[
                    CanonicalQueryColumn(column_name="event_time", time_grain="day"),
                ],
                metrics=[
                    CanonicalQueryMetric(
                        metric_name="Target",
                        expression="SUM(target)",
                    )
                ],
            ),
        ],
        visualization=CanonicalVisualization(
            source_id=chart_source_id,
            name=f"analytic_{suffix}",
            viz_type=VizType.MIXED_CHART,
            options={
                "query_encodings": [
                    {"position": 0, "series_type": "bar", "y_axis_index": 0},
                    {"position": 1, "series_type": "line", "y_axis_index": 1},
                ]
            },
        ),
    )

    first = analytics.replace_analytic(dataset=dataset, canonical=analytic_payload)
    session.flush()
    first_id = first.id

    # Mutate and re-ingest: should update same analytic, replace query graph.
    analytic_payload.name = f"analytic_{suffix}_v2"
    analytic_payload.queries = analytic_payload.queries[:1]
    second = analytics.replace_analytic(dataset=dataset, canonical=analytic_payload)
    session.flush()

    assert second.id == first_id
    assert second.name.endswith("_v2")

    queries = session.scalars(
        select(Query).where(Query.analytic_id == first_id).order_by(Query.position)
    ).all()
    assert len(queries) == 1
    assert queries[0].position == 0
    assert queries[0].row_limit == 100

    dataset_count = len(
        session.scalars(
            select(Dataset).where(
                Dataset.data_source_id == data_source.id,
                Dataset.source_id == dataset_source_id,
            )
        ).all()
    )
    assert dataset_count == 1

    analytic_count = len(
        session.scalars(
            select(Analytic).where(
                Analytic.dataset_id == dataset.id,
                Analytic.source_id == chart_source_id,
            )
        ).all()
    )
    assert analytic_count == 1

    session.rollback()
