import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.market_data.validation import TIMEFRAMES
from app.models.market_data import IngestionRun, Instrument, MarketCandle

router = APIRouter(prefix="/api/market-data", tags=["market-data"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/coverage")
def coverage(db: Db) -> dict[str, object]:
    instrument_count = db.scalar(select(func.count()).select_from(Instrument)) or 0
    row = db.execute(
        select(
            func.count(MarketCandle.id),
            func.min(MarketCandle.candle_timestamp),
            func.max(MarketCandle.candle_timestamp),
        )
    ).one()
    synthetic_count = db.scalar(
        select(func.count()).select_from(MarketCandle).where(MarketCandle.is_synthetic.is_(True))
    )
    groups = db.execute(
        select(Instrument.instrument_type, MarketCandle.timeframe, func.count(MarketCandle.id))
        .join(MarketCandle)
        .group_by(Instrument.instrument_type, MarketCandle.timeframe)
        .order_by(Instrument.instrument_type, MarketCandle.timeframe)
    ).all()
    return {
        "instruments_stored": instrument_count,
        "candle_count": row[0],
        "earliest_candle_timestamp": row[1],
        "latest_candle_timestamp": row[2],
        "contains_synthetic_data": bool(synthetic_count),
        "coverage": [
            {"instrument_type": item[0], "timeframe": item[1], "candle_count": item[2]}
            for item in groups
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
                "token": x.token,
                "trading_symbol": x.trading_symbol,
                "underlying_symbol": x.underlying_symbol,
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
                "candle_timestamp": x.candle_timestamp,
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
                "started_at": x.started_at,
                "completed_at": x.completed_at,
                "records_received": x.records_received,
                "records_inserted": x.records_inserted,
                "records_updated": x.records_updated,
                "records_rejected": x.records_rejected,
                "error_summary": x.error_summary,
                "is_synthetic": x.is_synthetic,
            }
            for x in items
        ],
    }
