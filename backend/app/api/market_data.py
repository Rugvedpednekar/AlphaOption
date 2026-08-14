import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.market_data.validation import TIMEFRAMES
from app.models.market_data import IngestionRun, Instrument, MarketCandle

router = APIRouter(prefix="/api/market-data", tags=["market-data"])
Db = Annotated[Session, Depends(get_db)]


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.get("/coverage")
def coverage(
    db: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, object]:
    instrument_ids = list(
        db.scalars(select(Instrument.id).order_by(Instrument.id).offset(offset).limit(limit)).all()
    )
    instrument_count = len(instrument_ids)
    row = db.execute(
        select(
            func.count(MarketCandle.id),
            func.min(MarketCandle.candle_timestamp),
            func.max(MarketCandle.candle_timestamp),
        ).where(MarketCandle.instrument_id.in_(instrument_ids))
    ).one()
    synthetic_count = db.scalar(
        select(func.count())
        .select_from(MarketCandle)
        .where(
            MarketCandle.instrument_id.in_(instrument_ids),
            MarketCandle.is_synthetic.is_(True),
        )
    )
    groups = db.execute(
        select(
            Instrument.id,
            Instrument.instrument_type,
            MarketCandle.timeframe,
            func.count(MarketCandle.id),
            func.min(MarketCandle.candle_timestamp),
            func.max(MarketCandle.candle_timestamp),
            func.sum(func.cast(MarketCandle.is_synthetic, Integer)),
        )
        .join(MarketCandle)
        .where(Instrument.id.in_(instrument_ids))
        .group_by(
            Instrument.id,
            Instrument.instrument_type,
            MarketCandle.timeframe,
        )
        .order_by(Instrument.instrument_type, Instrument.id, MarketCandle.timeframe)
    ).all()
    return {
        "instruments_stored": instrument_count,
        "candle_count": row[0],
        "earliest_candle_timestamp": _utc(row[1]),
        "latest_candle_timestamp": _utc(row[2]),
        "contains_synthetic_data": bool(synthetic_count),
        "scope": "paginated_instruments",
        "gap_method": "raw_interval_slots",
        "offset": offset,
        "limit": limit,
        "coverage": [
            {
                "instrument_id": str(item[0]),
                "instrument_type": item[1],
                "timeframe": item[2],
                "candle_count": item[3],
                "first_candle": _utc(item[4]),
                "last_candle": _utc(item[5]),
                "raw_gap_count": _raw_gap_count(item[3], item[4], item[5], item[2]),
                "gap_method": "raw_interval_slots",
                "is_synthetic": bool(item[6]),
            }
            for item in groups
        ],
    }


def _raw_gap_count(
    count: int, first: datetime | None, last: datetime | None, timeframe: str
) -> int:
    if not first or not last or timeframe not in {"1m", "5m"}:
        return 0
    seconds = 60 if timeframe == "1m" else 300
    expected = int((last - first).total_seconds() / seconds) + 1
    return max(expected - count, 0)


@router.get("/gaps")
def gaps(
    db: Db, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> dict[str, object]:
    result = coverage(db, offset, limit)
    return {
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "instrument_id": row["instrument_id"],
                "timeframe": row["timeframe"],
                "raw_gap_count": row["raw_gap_count"],
                "gap_method": "raw_interval_slots",
            }
            for row in result["coverage"]
        ],
    }


@router.get("/instruments")
def instruments(
    db: Db,
    provider: str | None = None,
    instrument_type: str | None = None,
    synthetic: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, object]:
    query = select(Instrument)
    if provider:
        query = query.where(Instrument.provider == provider)
    if instrument_type:
        if instrument_type not in {"spot", "future", "option"}:
            raise HTTPException(422, "unsupported instrument_type")
        query = query.where(Instrument.instrument_type == instrument_type)
    if synthetic is not None:
        query = query.where(Instrument.is_synthetic == synthetic)
    items = db.scalars(query.order_by(Instrument.trading_symbol).offset(offset).limit(limit)).all()
    return {
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": str(x.id),
                "provider": x.provider,
                "exchange": x.exchange,
                "instrument_type": x.instrument_type,
                "expiry": x.expiry,
                "strike": x.strike,
                "option_type": x.option_type,
                "lot_size": x.lot_size,
                "tick_size": x.tick_size,
                "active": x.active,
                "is_synthetic": x.is_synthetic,
            }
            for x in items
        ],
    }


@router.get("/instruments/{instrument_id}/candles")
def candles(
    instrument_id: uuid.UUID,
    db: Db,
    timeframe: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, object]:
    if timeframe and timeframe not in TIMEFRAMES:
        raise HTTPException(422, "unsupported timeframe")
    if start and (start.tzinfo is None or start.utcoffset() is None):
        raise HTTPException(422, "start must include timezone")
    if end and (end.tzinfo is None or end.utcoffset() is None):
        raise HTTPException(422, "end must include timezone")
    if start and end and start > end:
        raise HTTPException(422, "start must not be after end")
    query = select(MarketCandle).where(MarketCandle.instrument_id == instrument_id)
    if timeframe:
        query = query.where(MarketCandle.timeframe == timeframe)
    if start:
        query = query.where(MarketCandle.candle_timestamp >= start)
    if end:
        query = query.where(MarketCandle.candle_timestamp <= end)
    items = db.scalars(query.order_by(MarketCandle.candle_timestamp.desc()).limit(limit)).all()
    return {
        "instrument_id": str(instrument_id),
        "items": [
            {
                "timeframe": x.timeframe,
                "candle_timestamp": _utc(x.candle_timestamp),
                "open": x.open,
                "high": x.high,
                "low": x.low,
                "close": x.close,
                "volume": x.volume,
                "open_interest": x.open_interest,
                "source": x.source,
                "is_synthetic": x.is_synthetic,
            }
            for x in items
        ],
    }


@router.get("/ingestion-runs")
def ingestion_runs(
    db: Db, offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> dict[str, object]:
    items = db.scalars(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).offset(offset).limit(limit)
    ).all()
    return {
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": str(x.id),
                "provider": x.provider,
                "dataset": x.dataset,
                "status": x.status,
                "started_at": _utc(x.started_at),
                "completed_at": _utc(x.completed_at),
                "records_received": x.records_received,
                "records_inserted": x.records_inserted,
                "records_updated": x.records_updated,
                "records_duplicates": x.records_duplicates,
                "records_rejected": x.records_rejected,
                "error_summary": x.error_summary,
                "is_synthetic": x.is_synthetic,
            }
            for x in items
        ],
    }
