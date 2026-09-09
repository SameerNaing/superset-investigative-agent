"""Unique data_source on (provider, name).

Revision ID: c3d5f9a2b014
Revises: b2c4e8f1a903
Create Date: 2026-09-07 05:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3d5f9a2b014"
down_revision: str | Sequence[str] | None = "b2c4e8f1a903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop legacy provider-only uniqueness if it was applied earlier.
    op.execute(
        "ALTER TABLE bi.data_source "
        "DROP CONSTRAINT IF EXISTS uq_data_source_provider"
    )
    op.create_unique_constraint(
        "uq_data_source_provider_name",
        "data_source",
        ["provider", "name"],
        schema="bi",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_data_source_provider_name",
        "data_source",
        schema="bi",
        type_="unique",
    )
