"""Add ingestion duplicate count.

Revision ID: 20260813_0003
Revises: 20260813_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260813_0003"
down_revision: str | None = "20260813_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column("records_duplicates", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_ingestion_duplicates_nonnegative",
        "ingestion_runs",
        "records_duplicates >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ingestion_duplicates_nonnegative", "ingestion_runs", type_="check")
    op.drop_column("ingestion_runs", "records_duplicates")
