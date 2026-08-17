"""Add resumable historical backfill state.

Revision ID: 20260813_0005
Revises: 20260813_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260813_0005"
down_revision: str | None = "20260813_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backfill_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("interval", sa.String(20), nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_chunks", sa.Integer(), nullable=False),
        sa.Column("successful_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("empty_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_duplicates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_category", sa.Text()),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("interval = 'FIVE_MINUTE'", name="ck_backfill_interval"),
        sa.CheckConstraint("status IN ('running','completed','failed')", name="ck_backfill_status"),
        sa.CheckConstraint("planned_chunks BETWEEN 1 AND 60", name="ck_backfill_planned_chunks"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backfill_runs_instrument_id", "backfill_runs", ["instrument_id"])
    op.create_table(
        "backfill_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("backfill_run_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("interval", sa.String(20), nullable=False),
        sa.Column("chunk_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chunk_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_classification", sa.String(12), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_duplicates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_category", sa.Text()),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running','completed','empty','failed')", name="ck_backfill_chunk_status"
        ),
        sa.CheckConstraint(
            "source_classification IN ('genuine','synthetic')", name="ck_backfill_chunk_source"
        ),
        sa.ForeignKeyConstraint(["backfill_run_id"], ["backfill_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instrument_id",
            "interval",
            "chunk_start",
            "chunk_end",
            "source_classification",
            name="uq_backfill_chunk_identity",
        ),
    )
    op.create_index("ix_backfill_chunks_backfill_run_id", "backfill_chunks", ["backfill_run_id"])
    op.create_index("ix_backfill_chunks_instrument_id", "backfill_chunks", ["instrument_id"])


def downgrade() -> None:
    op.drop_index("ix_backfill_chunks_instrument_id", table_name="backfill_chunks")
    op.drop_index("ix_backfill_chunks_backfill_run_id", table_name="backfill_chunks")
    op.drop_table("backfill_chunks")
    op.drop_index("ix_backfill_runs_instrument_id", table_name="backfill_runs")
    op.drop_table("backfill_runs")
