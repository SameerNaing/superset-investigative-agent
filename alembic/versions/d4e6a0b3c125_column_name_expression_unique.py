"""Allow same column name with different expressions.

Revision ID: d4e6a0b3c125
Revises: c3d5f9a2b014
Create Date: 2026-09-09 13:40:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4e6a0b3c125"
down_revision: str | Sequence[str] | None = "c3d5f9a2b014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_dataset_column_dataset_name",
        "dataset_column",
        schema="bi",
        type_="unique",
    )
    # NULLS NOT DISTINCT so two physical columns (expression IS NULL) with the
    # same name remain unique, while adhoc (name, expression) pairs can coexist.
    op.execute(
        """
        ALTER TABLE bi.dataset_column
        ADD CONSTRAINT uq_dataset_column_dataset_name_expression
        UNIQUE NULLS NOT DISTINCT (dataset_id, name, expression)
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_dataset_column_dataset_name_expression",
        "dataset_column",
        schema="bi",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_dataset_column_dataset_name",
        "dataset_column",
        ["dataset_id", "name"],
        schema="bi",
    )
