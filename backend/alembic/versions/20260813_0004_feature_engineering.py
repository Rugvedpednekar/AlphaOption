"""Create normalized feature engineering tables.

Revision ID: 20260813_0004
Revises: 20260813_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260813_0004"
down_revision: str | None = "20260813_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FEATURE_COLUMNS = (
    "simple_return_1",
    "simple_return_3",
    "simple_return_6",
    "log_return_1",
    "log_return_3",
    "log_return_6",
    "range_close",
    "body_open",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "gap_previous_close",
    "ema_9",
    "ema_21",
    "ema_spread_close",
    "close_distance_ema_9",
    "close_distance_ema_21",
    "ema_9_slope",
    "ema_21_slope",
    "rsi_14",
    "true_range",
    "atr_14",
    "atr_close",
    "log_return_std_12",
    "log_return_std_36",
    "volume_pct_change",
    "volume_mean_20",
    "volume_std_20",
    "volume_zscore",
)


def upgrade() -> None:
    op.create_table(
        "feature_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("requested_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(80), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("source_classification", sa.String(12), nullable=False),
        sa.Column("records_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_category", sa.Text()),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')", name="ck_feature_run_status"
        ),
        sa.CheckConstraint(
            "records_received >= 0 AND records_created >= 0 "
            "AND records_skipped >= 0 AND records_rejected >= 0",
            name="ck_feature_run_counts",
        ),
        sa.CheckConstraint(
            "source_classification IN ('genuine','synthetic')", name="ck_feature_run_source"
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feature_runs_instrument_id", "feature_runs", ["instrument_id"])
    columns = [sa.Column(name, sa.Float()) for name in FEATURE_COLUMNS]
    op.create_table(
        "market_features",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_run_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("candle_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(80), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("source_classification", sa.String(12), nullable=False),
        sa.Column("is_usable", sa.Boolean(), nullable=False),
        *columns,
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("minute_from_open", sa.Integer(), nullable=False),
        sa.Column("intraday_sin", sa.Float(), nullable=False),
        sa.Column("intraday_cos", sa.Float(), nullable=False),
        sa.Column("is_opening_session", sa.Boolean(), nullable=False),
        sa.Column("is_closing_session", sa.Boolean(), nullable=False),
        sa.Column("target_threshold", sa.Float()),
        sa.Column("future_return_15m", sa.Float()),
        sa.Column("future_return_30m", sa.Float()),
        sa.Column("direction_15m", sa.String(8)),
        sa.Column("direction_30m", sa.String(8)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("interval = '5m'", name="ck_market_feature_interval"),
        sa.CheckConstraint(
            "source_classification IN ('genuine','synthetic')", name="ck_market_feature_source"
        ),
        sa.CheckConstraint(
            "direction_15m IS NULL OR direction_15m IN ('up','down','neutral')",
            name="ck_market_feature_direction_15m",
        ),
        sa.CheckConstraint(
            "direction_30m IS NULL OR direction_30m IN ('up','down','neutral')",
            name="ck_market_feature_direction_30m",
        ),
        sa.CheckConstraint(
            "target_threshold IS NULL OR target_threshold >= 0", name="ck_target_threshold"
        ),
        sa.ForeignKeyConstraint(["feature_run_id"], ["feature_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instrument_id",
            "interval",
            "candle_timestamp",
            "feature_version",
            name="uq_market_feature_identity",
        ),
    )
    op.create_index("ix_market_features_instrument_id", "market_features", ["instrument_id"])
    op.create_index("ix_market_features_candle_timestamp", "market_features", ["candle_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_market_features_candle_timestamp", table_name="market_features")
    op.drop_index("ix_market_features_instrument_id", table_name="market_features")
    op.drop_table("market_features")
    op.drop_index("ix_feature_runs_instrument_id", table_name="feature_runs")
    op.drop_table("feature_runs")
