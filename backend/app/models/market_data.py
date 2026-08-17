import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint(
            "provider", "exchange", "token", name="uq_instrument_provider_exchange_token"
        ),
        CheckConstraint("lot_size > 0", name="ck_instrument_lot_positive"),
        CheckConstraint("tick_size > 0", name="ck_instrument_tick_positive"),
        CheckConstraint("strike IS NULL OR strike >= 0", name="ck_instrument_strike_nonnegative"),
        CheckConstraint("instrument_type IN ('spot','future','option')", name="ck_instrument_type"),
        CheckConstraint(
            "option_type IS NULL OR option_type IN ('CE','PE')", name="ck_instrument_option_type"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    token: Mapped[str] = mapped_column(String(100), nullable=False)
    trading_symbol: Mapped[str] = mapped_column(String(160), nullable=False)
    underlying_symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(20), nullable=False)
    expiry: Mapped[date | None] = mapped_column(Date)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    option_type: Mapped[str | None] = mapped_column(String(4))
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    candles: Mapped[list["MarketCandle"]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "timeframe",
            "candle_timestamp",
            "source",
            name="uq_market_candle_identity",
        ),
        CheckConstraint(
            "timeframe IN ('1m','5m','15m','30m','1h','1d')", name="ck_candle_timeframe"
        ),
        CheckConstraint("volume >= 0", name="ck_candle_volume_nonnegative"),
        CheckConstraint(
            "open_interest IS NULL OR open_interest >= 0", name="ck_candle_oi_nonnegative"
        ),
        CheckConstraint(
            "low >= 0 AND high >= open AND high >= close "
            "AND high >= low AND low <= open AND low <= close",
            name="ck_candle_ohlc",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    candle_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open_interest: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    instrument: Mapped[Instrument] = relationship(back_populates="candles")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','completed','completed_with_rejections','failed')",
            name="ck_ingestion_status",
        ),
        CheckConstraint(
            "records_received >= 0 AND records_inserted >= 0 "
            "AND records_updated >= 0 AND records_rejected >= 0",
            name="ck_ingestion_counts",
        ),
        CheckConstraint("records_duplicates >= 0", name="ck_ingestion_duplicates_nonnegative"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_duplicates: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class BackfillRun(Base):
    __tablename__ = "backfill_runs"
    __table_args__ = (
        CheckConstraint("interval = 'FIVE_MINUTE'", name="ck_backfill_interval"),
        CheckConstraint("status IN ('running','completed','failed')", name="ck_backfill_status"),
        CheckConstraint("planned_chunks BETWEEN 1 AND 60", name="ck_backfill_planned_chunks"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    successful_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    empty_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    error_category: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackfillChunk(Base):
    __tablename__ = "backfill_chunks"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "interval",
            "chunk_start",
            "chunk_end",
            "source_classification",
            name="uq_backfill_chunk_identity",
        ),
        CheckConstraint(
            "status IN ('running','completed','empty','failed')", name="ck_backfill_chunk_status"
        ),
        CheckConstraint(
            "source_classification IN ('genuine','synthetic')", name="ck_backfill_chunk_source"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    backfill_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("backfill_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    chunk_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chunk_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_classification: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_category: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
