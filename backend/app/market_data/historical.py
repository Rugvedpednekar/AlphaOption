import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.market_data.provider import CandleRecord, HistoricalCandleProvider, InstrumentRecord
from app.market_data.validation import validate_candle
from app.models.market_data import IngestionRun, Instrument, MarketCandle

logger = logging.getLogger(__name__)

INTERVALS = {
    "ONE_MINUTE": ("1m", timedelta(minutes=1), timedelta(days=7)),
    "FIVE_MINUTE": ("5m", timedelta(minutes=5), timedelta(days=30)),
}
MAX_AUTHORIZED_RANGE = timedelta(days=366)


class HistoricalIngestionError(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


@dataclass(frozen=True)
class HistoricalRequest:
    instrument_id: uuid.UUID
    interval: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class HistoricalChunk:
    """A half-open UTC interval: start is included and end is excluded."""

    start: datetime
    end: datetime


def normalize_request(request: HistoricalRequest, now: datetime | None = None) -> HistoricalRequest:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    if request.interval not in INTERVALS:
        raise HistoricalIngestionError("unsupported-interval")
    if any(
        not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None
        for value in (request.start, request.end)
    ):
        raise HistoricalIngestionError("timezone-required")
    start, end = request.start.astimezone(UTC), request.end.astimezone(UTC)
    if start >= end:
        raise HistoricalIngestionError("invalid-range")
    if end > current:
        raise HistoricalIngestionError("future-range")
    if end - start > MAX_AUTHORIZED_RANGE:
        raise HistoricalIngestionError("range-too-large")
    return HistoricalRequest(request.instrument_id, request.interval, start, end)


def build_chunks(
    request: HistoricalRequest, chunk_range: timedelta | None = None
) -> list[HistoricalChunk]:
    limit = chunk_range or INTERVALS[request.interval][2]
    if limit <= timedelta(0):
        raise HistoricalIngestionError("invalid-chunk-range")
    chunks: list[HistoricalChunk] = []
    cursor = request.start
    while cursor < request.end:
        boundary = min(cursor + limit, request.end)
        chunks.append(HistoricalChunk(cursor, boundary))
        cursor = boundary
    return chunks


def instrument_record(value: Instrument) -> InstrumentRecord:
    return InstrumentRecord(
        provider=value.provider,
        exchange=value.exchange,
        token=value.token,
        trading_symbol=value.trading_symbol,
        underlying_symbol=value.underlying_symbol,
        instrument_type=value.instrument_type,
        expiry=value.expiry,
        strike=value.strike,
        option_type=value.option_type,
        lot_size=value.lot_size,
        tick_size=value.tick_size,
        active=value.active,
        is_synthetic=value.is_synthetic,
    )


def _identity_query(instrument_id: uuid.UUID, item: CandleRecord, timestamp: datetime):
    return select(MarketCandle).where(
        MarketCandle.instrument_id == instrument_id,
        MarketCandle.timeframe == item.timeframe,
        MarketCandle.candle_timestamp == timestamp,
        MarketCandle.source == item.source,
    )


def _same_values(existing: MarketCandle, item: CandleRecord) -> bool:
    return (
        existing.open,
        existing.high,
        existing.low,
        existing.close,
        existing.volume,
        existing.open_interest,
        existing.is_synthetic,
    ) == (
        item.open,
        item.high,
        item.low,
        item.close,
        item.volume,
        item.open_interest,
        item.is_synthetic,
    )


def _store_candle(
    session: Session,
    instrument: Instrument,
    item: CandleRecord,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> tuple[str, datetime]:
    validate_candle(item)
    if item.timeframe != timeframe:
        raise ValueError("unexpected-interval")
    if (item.provider, item.exchange, item.token) != (
        instrument.provider,
        instrument.exchange,
        instrument.token,
    ):
        raise ValueError("instrument-metadata-conflict")
    timestamp = item.candle_timestamp.astimezone(UTC)
    if not start <= timestamp < end:
        raise ValueError("timestamp-outside-requested-chunk")
    query = _identity_query(instrument.id, item, timestamp)
    existing = session.scalar(query)
    if existing is not None:
        if not _same_values(existing, item):
            raise ValueError("conflicting-candle")
        return "duplicate", timestamp
    candidate = MarketCandle(
        instrument_id=instrument.id,
        timeframe=timeframe,
        candle_timestamp=timestamp,
        open=item.open,
        high=item.high,
        low=item.low,
        close=item.close,
        volume=item.volume,
        open_interest=item.open_interest,
        source=item.source,
        is_synthetic=item.is_synthetic,
    )
    try:
        with session.begin_nested():
            session.add(candidate)
            session.flush()
    except IntegrityError:
        # The unique constraint is authoritative under concurrent ingestion.
        session.expire_all()
        existing = session.scalar(query)
        if existing is None:
            raise
        if not _same_values(existing, item):
            raise ValueError("conflicting-candle") from None
        return "duplicate", timestamp
    return "inserted", timestamp


def _commit_failure_audit(
    session: Session,
    provider: HistoricalCandleProvider,
    request: HistoricalRequest,
    timeframe: str,
    started_at: datetime,
    received: int,
    duplicates: int,
    category: str,
) -> None:
    session.rollback()
    run = IngestionRun(
        provider=provider.name,
        dataset=f"historical:{request.instrument_id}:{timeframe}",
        status="failed",
        started_at=started_at,
        completed_at=datetime.now(UTC),
        records_received=received,
        records_duplicates=min(duplicates, received),
        records_rejected=max(received - duplicates, 0),
        error_summary=category,
        is_synthetic=provider.is_synthetic,
    )
    session.add(run)
    session.commit()


def ingest_history(
    session: Session,
    provider: HistoricalCandleProvider,
    request: HistoricalRequest,
    *,
    throttle_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> IngestionRun:
    started_at = datetime.now(UTC)
    normalized = normalize_request(request, now)
    timeframe = INTERVALS[normalized.interval][0]
    received = duplicates = rejected = 0
    provider_closed = False
    try:
        instrument = session.get(Instrument, normalized.instrument_id)
        if instrument is None or not instrument.active:
            raise HistoricalIngestionError("instrument-not-registered")
        run = IngestionRun(
            provider=provider.name,
            dataset=f"historical:{instrument.id}:{timeframe}",
            status="running",
            started_at=started_at,
            is_synthetic=provider.is_synthetic,
        )
        session.add(run)
        session.flush()
        seen: set[datetime] = set()
        errors: list[str] = []
        for index, chunk in enumerate(build_chunks(normalized)):
            if index and throttle_seconds:
                sleep(throttle_seconds)
            batch = provider.historical_candles(
                instrument_record(instrument), normalized.interval, chunk.start, chunk.end
            )
            received += len(batch.rows)
            if not batch.complete:
                raise HistoricalIngestionError("incomplete-provider-response")
            for row in batch.rows:
                try:
                    result, timestamp = _store_candle(
                        session, instrument, row, timeframe, chunk.start, chunk.end
                    )
                    if timestamp in seen:
                        raise ValueError("duplicate-provider-candle")
                    seen.add(timestamp)
                    if result == "inserted":
                        run.records_inserted += 1
                    else:
                        duplicates += 1
                except (AttributeError, TypeError, ValueError, OverflowError):
                    rejected += 1
                    errors.append("candle-validation-rejected")
        run.records_received = received
        run.records_duplicates = duplicates
        run.records_rejected = rejected
        if received != run.records_inserted + duplicates + rejected:
            raise HistoricalIngestionError("ingestion-count-mismatch")
        run.status = "completed_with_rejections" if rejected else "completed"
        run.completed_at = datetime.now(UTC)
        run.error_summary = "; ".join(errors[:20]) or None
        provider.close()
        provider_closed = True
        session.commit()
        session.refresh(run)
        return run
    except Exception as exc:
        if not provider_closed:
            try:
                provider.close()
            except Exception:
                logger.warning(
                    "historical provider cleanup failed",
                    extra={"context": {"category": "session-cleanup-failure"}},
                )
        category = (
            exc.category
            if isinstance(exc, HistoricalIngestionError)
            else "database-connection-failure"
            if isinstance(exc, SQLAlchemyError)
            else "provider-or-persistence-failure"
        )
        _commit_failure_audit(
            session,
            provider,
            normalized,
            timeframe,
            started_at,
            received,
            duplicates,
            category,
        )
        logger.warning("historical ingestion failed", extra={"context": {"category": category}})
        raise HistoricalIngestionError(category) from None
