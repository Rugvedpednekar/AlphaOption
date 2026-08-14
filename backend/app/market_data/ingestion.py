import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import redact
from app.market_data.provider import MarketDataProvider
from app.market_data.validation import validate_candle
from app.models.market_data import IngestionRun, Instrument, MarketCandle

logger = logging.getLogger(__name__)


def ingest_provider(session: Session, provider: MarketDataProvider) -> IngestionRun:
    instruments, candles = provider.instruments(), provider.candles()
    run = IngestionRun(
        provider=provider.name,
        dataset=provider.dataset,
        status="running",
        started_at=datetime.now(UTC),
        records_received=len(instruments) + len(candles),
        is_synthetic=provider.is_synthetic,
    )
    session.add(run)
    session.flush()
    rejected: list[str] = []
    instrument_map: dict[tuple[str, str, str], Instrument] = {}
    for item in instruments:
        key = (item.provider, item.exchange, item.token)
        existing = session.scalar(
            select(Instrument).where(
                Instrument.provider == item.provider,
                Instrument.exchange == item.exchange,
                Instrument.token == item.token,
            )
        )
        values = {
            name: getattr(item, name)
            for name in (
                "trading_symbol",
                "underlying_symbol",
                "instrument_type",
                "expiry",
                "strike",
                "option_type",
                "lot_size",
                "tick_size",
                "active",
                "is_synthetic",
            )
        }
        if existing is None:
            existing = Instrument(
                provider=item.provider, exchange=item.exchange, token=item.token, **values
            )
            session.add(existing)
            session.flush()
            run.records_inserted += 1
        elif any(getattr(existing, name) != value for name, value in values.items()):
            for name, value in values.items():
                setattr(existing, name, value)
            run.records_updated += 1
        instrument_map[key] = existing
    for item in candles:
        try:
            validate_candle(item)
            instrument = instrument_map[(item.provider, item.exchange, item.token)]
            existing = session.scalar(
                select(MarketCandle).where(
                    MarketCandle.instrument_id == instrument.id,
                    MarketCandle.timeframe == item.timeframe,
                    MarketCandle.candle_timestamp == item.candle_timestamp,
                    MarketCandle.source == item.source,
                )
            )
            values = (
                item.open,
                item.high,
                item.low,
                item.close,
                item.volume,
                item.open_interest,
                item.is_synthetic,
            )
            if existing is not None:
                if values != (
                    existing.open,
                    existing.high,
                    existing.low,
                    existing.close,
                    existing.volume,
                    existing.open_interest,
                    existing.is_synthetic,
                ):
                    raise ValueError("duplicate candle conflicts with stored data")
                run.records_duplicates += 1
                continue
            session.add(
                MarketCandle(
                    instrument_id=instrument.id,
                    timeframe=item.timeframe,
                    candle_timestamp=item.candle_timestamp,
                    open=item.open,
                    high=item.high,
                    low=item.low,
                    close=item.close,
                    volume=item.volume,
                    open_interest=item.open_interest,
                    source=item.source,
                    is_synthetic=item.is_synthetic,
                )
            )
            run.records_inserted += 1
        except (ValueError, KeyError) as exc:
            run.records_rejected += 1
            rejected.append(str(exc))
    run.status = "completed_with_rejections" if rejected else "completed"
    run.completed_at = datetime.now(UTC)
    run.error_summary = "; ".join(rejected)[:1000] or None
    session.commit()
    session.refresh(run)
    logger.info(
        "market data ingestion completed",
        extra={
            "context": redact(
                {
                    "provider": provider.name,
                    "dataset": provider.dataset,
                    "inserted": run.records_inserted,
                    "updated": run.records_updated,
                    "rejected": run.records_rejected,
                }
            )
        },
    )
    return run
