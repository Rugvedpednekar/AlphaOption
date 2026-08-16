import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeatureRun(Base):
    __tablename__ = "feature_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running','completed','failed')", name="ck_feature_run_status"),
        CheckConstraint(
            "records_received >= 0 AND records_created >= 0 AND "
            "records_skipped >= 0 AND records_rejected >= 0",
            name="ck_feature_run_counts",
        ),
        CheckConstraint(
            "source_classification IN ('genuine','synthetic')",
            name="ck_feature_run_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_classification: Mapped[str] = mapped_column(String(12), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    error_category: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MarketFeature(Base):
    __tablename__ = "market_features"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "interval",
            "candle_timestamp",
            "feature_version",
            name="uq_market_feature_identity",
        ),
        CheckConstraint("interval = '5m'", name="ck_market_feature_interval"),
        CheckConstraint(
            "source_classification IN ('genuine','synthetic')",
            name="ck_market_feature_source",
        ),
        CheckConstraint(
            "direction_15m IS NULL OR direction_15m IN ('up','down','neutral')",
            name="ck_market_feature_direction_15m",
        ),
        CheckConstraint(
            "direction_30m IS NULL OR direction_30m IN ('up','down','neutral')",
            name="ck_market_feature_direction_30m",
        ),
        CheckConstraint(
            "target_threshold IS NULL OR target_threshold >= 0", name="ck_target_threshold"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    feature_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feature_runs.id", ondelete="RESTRICT"), nullable=False
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    candle_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    feature_version: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_classification: Mapped[str] = mapped_column(String(12), nullable=False)
    is_usable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    simple_return_1: Mapped[float | None] = mapped_column(Float)
    simple_return_3: Mapped[float | None] = mapped_column(Float)
    simple_return_6: Mapped[float | None] = mapped_column(Float)
    log_return_1: Mapped[float | None] = mapped_column(Float)
    log_return_3: Mapped[float | None] = mapped_column(Float)
    log_return_6: Mapped[float | None] = mapped_column(Float)
    range_close: Mapped[float | None] = mapped_column(Float)
    body_open: Mapped[float | None] = mapped_column(Float)
    upper_wick_ratio: Mapped[float | None] = mapped_column(Float)
    lower_wick_ratio: Mapped[float | None] = mapped_column(Float)
    gap_previous_close: Mapped[float | None] = mapped_column(Float)
    ema_9: Mapped[float | None] = mapped_column(Float)
    ema_21: Mapped[float | None] = mapped_column(Float)
    ema_spread_close: Mapped[float | None] = mapped_column(Float)
    close_distance_ema_9: Mapped[float | None] = mapped_column(Float)
    close_distance_ema_21: Mapped[float | None] = mapped_column(Float)
    ema_9_slope: Mapped[float | None] = mapped_column(Float)
    ema_21_slope: Mapped[float | None] = mapped_column(Float)
    rsi_14: Mapped[float | None] = mapped_column(Float)
    true_range: Mapped[float | None] = mapped_column(Float)
    atr_14: Mapped[float | None] = mapped_column(Float)
    atr_close: Mapped[float | None] = mapped_column(Float)
    log_return_std_12: Mapped[float | None] = mapped_column(Float)
    log_return_std_36: Mapped[float | None] = mapped_column(Float)
    volume_pct_change: Mapped[float | None] = mapped_column(Float)
    volume_mean_20: Mapped[float | None] = mapped_column(Float)
    volume_std_20: Mapped[float | None] = mapped_column(Float)
    volume_zscore: Mapped[float | None] = mapped_column(Float)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    minute_from_open: Mapped[int] = mapped_column(Integer, nullable=False)
    intraday_sin: Mapped[float] = mapped_column(Float, nullable=False)
    intraday_cos: Mapped[float] = mapped_column(Float, nullable=False)
    is_opening_session: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_closing_session: Mapped[bool] = mapped_column(Boolean, nullable=False)

    target_threshold: Mapped[float | None] = mapped_column(Float)
    future_return_15m: Mapped[float | None] = mapped_column(Float)
    future_return_30m: Mapped[float | None] = mapped_column(Float)
    direction_15m: Mapped[str | None] = mapped_column(String(8))
    direction_30m: Mapped[str | None] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
