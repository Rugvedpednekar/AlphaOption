import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.market_data.historical import (
    HistoricalChunk,
    HistoricalIngestionError,
    HistoricalRequest,
    _store_candle,
    build_chunks,
    instrument_record,
)
from app.market_data.historical_providers import validate_nifty_identity
from app.market_data.provider import HistoricalCandleProvider
from app.models.market_data import BackfillChunk, BackfillRun, Instrument

logger = logging.getLogger(__name__)
MAX_BACKFILL_REQUESTS = 60
BACKFILL_CHUNK_RANGE = timedelta(days=30)


@dataclass(frozen=True)
class BackfillPlan:
    requested_start: datetime
    requested_end: datetime
    actual_start: datetime
    chunks: tuple[HistoricalChunk, ...]


def plan_backfill(request: HistoricalRequest, now: datetime | None = None) -> BackfillPlan:
    if request.interval != "FIVE_MINUTE":
        raise HistoricalIngestionError("unsupported-backfill-interval")
    if any(
        value.tzinfo is None or value.utcoffset() is None for value in (request.start, request.end)
    ):
        raise HistoricalIngestionError("timezone-required")
    start, end = request.start.astimezone(UTC), request.end.astimezone(UTC)
    if start >= end:
        raise HistoricalIngestionError("invalid-range")
    if end > (now or datetime.now(UTC)).astimezone(UTC):
        raise HistoricalIngestionError("future-range")
    requested_chunks = build_chunks(
        HistoricalRequest(request.instrument_id, request.interval, start, end), BACKFILL_CHUNK_RANGE
    )
    chunks = requested_chunks[-MAX_BACKFILL_REQUESTS:]
    actual_start = chunks[0].start
    return BackfillPlan(start, end, actual_start, tuple(chunks))


def _completed_chunk(
    session: Session, instrument_id: uuid.UUID, chunk: HistoricalChunk, source: str
) -> bool:
    return (
        session.scalar(
            select(BackfillChunk.id).where(
                BackfillChunk.instrument_id == instrument_id,
                BackfillChunk.interval == "FIVE_MINUTE",
                BackfillChunk.chunk_start == chunk.start,
                BackfillChunk.chunk_end == chunk.end,
                BackfillChunk.source_classification == source,
                BackfillChunk.status.in_(("completed", "empty")),
            )
        )
        is not None
    )


def _chunk_row(
    session: Session, instrument_id: uuid.UUID, chunk: HistoricalChunk, source: str
) -> BackfillChunk | None:
    return session.scalar(
        select(BackfillChunk).where(
            BackfillChunk.instrument_id == instrument_id,
            BackfillChunk.interval == "FIVE_MINUTE",
            BackfillChunk.chunk_start == chunk.start,
            BackfillChunk.chunk_end == chunk.end,
            BackfillChunk.source_classification == source,
        )
    )


def execute_backfill(
    session: Session,
    provider: HistoricalCandleProvider,
    request: HistoricalRequest,
    *,
    throttle_seconds: float = 1.1,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> BackfillRun:
    plan = plan_backfill(request, now)
    source = "synthetic" if provider.is_synthetic else "genuine"
    instrument = session.get(Instrument, request.instrument_id)
    if instrument is None or not instrument.active:
        raise HistoricalIngestionError("instrument-not-registered")
    if instrument.instrument_type != "spot":
        raise HistoricalIngestionError("instrument-identity-rejected")
    validate_nifty_identity(instrument_record(instrument), now or datetime.now(UTC))
    if instrument.is_synthetic != provider.is_synthetic:
        raise HistoricalIngestionError("instrument-source-classification-mismatch")
    run = BackfillRun(
        instrument_id=instrument.id,
        provider=provider.name,
        interval="FIVE_MINUTE",
        requested_start=plan.requested_start,
        requested_end=plan.requested_end,
        actual_start=plan.actual_start,
        planned_chunks=len(plan.chunks),
        status="running",
    )
    session.add(run)
    session.commit()
    requested = 0
    try:
        for chunk in plan.chunks:
            if _completed_chunk(session, instrument.id, chunk, source):
                run.skipped_chunks += 1
                session.commit()
                continue
            if requested:
                sleep(max(throttle_seconds, 1.1))
            chunk_audit = _chunk_row(session, instrument.id, chunk, source)
            if chunk_audit is None:
                chunk_audit = BackfillChunk(
                    backfill_run_id=run.id,
                    instrument_id=instrument.id,
                    interval="FIVE_MINUTE",
                    chunk_start=chunk.start,
                    chunk_end=chunk.end,
                    source_classification=source,
                    status="running",
                )
                session.add(chunk_audit)
            else:
                chunk_audit.backfill_run_id = run.id
                chunk_audit.status = "running"
                chunk_audit.error_category = None
            chunk_audit.records_received = 0
            chunk_audit.records_inserted = 0
            chunk_audit.records_duplicates = 0
            chunk_audit.records_rejected = 0
            chunk_audit.completed_at = None
            session.commit()
            chunk_received = chunk_inserted = chunk_duplicates = chunk_rejected = 0
            try:
                batch = provider.historical_candles(
                    instrument_record(instrument), "FIVE_MINUTE", chunk.start, chunk.end
                )
                requested += 1
                if not batch.complete:
                    raise HistoricalIngestionError("incomplete-provider-response")
                seen: set[datetime] = set()
                for row in batch.rows:
                    chunk_received += 1
                    try:
                        result, timestamp = _store_candle(
                            session, instrument, row, "5m", chunk.start, chunk.end
                        )
                        if timestamp in seen:
                            raise ValueError("duplicate-provider-candle")
                        seen.add(timestamp)
                        if result == "inserted":
                            chunk_inserted += 1
                        else:
                            chunk_duplicates += 1
                    except (AttributeError, TypeError, ValueError, OverflowError):
                        chunk_rejected += 1
                if chunk_received != chunk_inserted + chunk_duplicates + chunk_rejected:
                    raise HistoricalIngestionError("ingestion-count-mismatch")
                chunk_audit = _chunk_row(session, instrument.id, chunk, source)
                chunk_audit.records_received = chunk_received
                chunk_audit.records_inserted = chunk_inserted
                chunk_audit.records_duplicates = chunk_duplicates
                chunk_audit.records_rejected = chunk_rejected
                chunk_audit.status = "empty" if not batch.rows else "completed"
                chunk_audit.completed_at = datetime.now(UTC)
                run.successful_chunks += 1
                run.empty_chunks += int(not batch.rows)
                run.records_received += chunk_received
                run.records_inserted += chunk_inserted
                run.records_duplicates += chunk_duplicates
                run.records_rejected += chunk_rejected
                session.commit()
            except Exception as exc:
                session.rollback()
                category = (
                    exc.category
                    if isinstance(exc, HistoricalIngestionError)
                    else "database-operation-failure"
                    if isinstance(exc, SQLAlchemyError)
                    else "provider-or-persistence-failure"
                )
                failed = _chunk_row(session, instrument.id, chunk, source)
                if failed is None:
                    failed = BackfillChunk(
                        backfill_run_id=run.id,
                        instrument_id=instrument.id,
                        interval="FIVE_MINUTE",
                        chunk_start=chunk.start,
                        chunk_end=chunk.end,
                        source_classification=source,
                        status="failed",
                    )
                    session.add(failed)
                failed.backfill_run_id = run.id
                failed.status = "failed"
                failed.error_category = category
                failed.records_received = chunk_received
                failed.records_inserted = 0
                failed.records_duplicates = chunk_duplicates
                failed.records_rejected = max(chunk_received - chunk_duplicates, 0)
                failed.completed_at = datetime.now(UTC)
                run = session.get(BackfillRun, run.id)
                run.failed_chunks += 1
                run.records_received += chunk_received
                run.records_duplicates += chunk_duplicates
                run.records_rejected += max(chunk_received - chunk_duplicates, 0)
                run.status = "failed"
                run.error_category = category
                run.completed_at = datetime.now(UTC)
                session.commit()
                raise HistoricalIngestionError(category) from None
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(run)
        return run
    finally:
        try:
            provider.close()
        except Exception:
            logger.warning(
                "backfill provider cleanup failed",
                extra={"context": {"category": "session-cleanup-failure"}},
            )
