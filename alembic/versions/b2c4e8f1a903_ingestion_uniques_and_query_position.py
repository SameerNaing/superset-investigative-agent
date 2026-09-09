"""Add ingestion uniqueness constraints and query.position.

Revision ID: b2c4e8f1a903
Revises: 988207abe701
Create Date: 2026-09-06 15:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c4e8f1a903"
down_revision: str | Sequence[str] | None = "988207abe701"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "query",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        schema="bi",
    )
    op.create_unique_constraint(
        "query_analytic_id_position_key",
        "query",
        ["analytic_id", "position"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_dataset_data_source_source_id",
        "dataset",
        ["data_source_id", "source_id"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_dataset_column_dataset_source_id",
        "dataset_column",
        ["dataset_id", "source_id"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_dataset_column_dataset_name",
        "dataset_column",
        ["dataset_id", "name"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_metric_dataset_source_id",
        "metric",
        ["dataset_id", "source_id"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_metric_dataset_name_expression",
        "metric",
        ["dataset_id", "name", "expression"],
        schema="bi",
    )
    op.create_unique_constraint(
        "uq_analytic_dataset_source_id",
        "analytic",
        ["dataset_id", "source_id"],
        schema="bi",
    )
    op.alter_column(
        "query",
        "position",
        server_default=None,
        schema="bi",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analytic_dataset_source_id",
        "analytic",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "uq_metric_dataset_name_expression",
        "metric",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "uq_metric_dataset_source_id",
        "metric",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "uq_dataset_column_dataset_name",
        "dataset_column",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "uq_dataset_column_dataset_source_id",
        "dataset_column",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "uq_dataset_data_source_source_id",
        "dataset",
        schema="bi",
        type_="unique",
    )
    op.drop_constraint(
        "query_analytic_id_position_key",
        "query",
        schema="bi",
        type_="unique",
    )
    op.drop_column("query", "position", schema="bi")
