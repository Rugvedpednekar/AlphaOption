"""Create provider-independent market data tables.

Revision ID: 20260813_0002
Revises: 20260813_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260813_0002"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("token", sa.String(100), nullable=False),
        sa.Column("trading_symbol", sa.String(160), nullable=False),
        sa.Column("underlying_symbol", sa.String(80), nullable=False),
        sa.Column("instrument_type", sa.String(20), nullable=False),
        sa.Column("expiry", sa.Date()),
        sa.Column("strike", sa.Numeric(18, 4)),
        sa.Column("option_type", sa.String(4)),
        sa.Column("lot_size", sa.Integer(), nullable=False),
        sa.Column("tick_size", sa.Numeric(12, 6), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("lot_size > 0", name="ck_instrument_lot_positive"),
        sa.CheckConstraint("tick_size > 0", name="ck_instrument_tick_positive"),
        sa.CheckConstraint(
            "strike IS NULL OR strike >= 0", name="ck_instrument_strike_nonnegative"
        ),
        sa.CheckConstraint(
            "instrument_type IN ('spot','future','option')", name="ck_instrument_type"
        ),
        sa.CheckConstraint(
            "option_type IS NULL OR option_type IN ('CE','PE')", name="ck_instrument_option_type"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "exchange", "token", name="uq_instrument_provider_exchange_token"
        ),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("dataset", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running','completed','completed_with_rejections','failed')",
            name="ck_ingestion_status",
        ),
        sa.CheckConstraint(
            "records_received >= 0 AND records_inserted >= 0 "
            "AND records_updated >= 0 AND records_rejected >= 0",
            name="ck_ingestion_counts",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "market_candles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("candle_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("open_interest", sa.BigInteger()),
        sa.Column("source", sa.String(60), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "timeframe IN ('1m','5m','15m','30m','1h','1d')", name="ck_candle_timeframe"
        ),
        sa.CheckConstraint("volume >= 0", name="ck_candle_volume_nonnegative"),
        sa.CheckConstraint(
            "open_interest IS NULL OR open_interest >= 0", name="ck_candle_oi_nonnegative"
        ),
        sa.CheckConstraint(
            "low >= 0 AND high >= open AND high >= close "
            "AND high >= low AND low <= open AND low <= close",
            name="ck_candle_ohlc",
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instrument_id",
            "timeframe",
            "candle_timestamp",
            "source",
            name="uq_market_candle_identity",
        ),
    )
    op.create_index("ix_market_candles_instrument_id", "market_candles", ["instrument_id"])
    op.create_index("ix_market_candles_candle_timestamp", "market_candles", ["candle_timestamp"])


def downgrade() -> None:
    op.drop_table("market_candles")
    op.drop_table("ingestion_runs")
    op.drop_table("instruments")
