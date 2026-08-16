import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.features.engine import MODEL_INPUT_FIELDS, TARGET_FIELDS
from app.models.features import FeatureRun, MarketFeature

router = APIRouter(prefix="/api/features", tags=["features"])
Db = Annotated[Session, Depends(get_db)]


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.get("/runs")
def runs(
    db: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    items = list(
        db.scalars(
            select(FeatureRun).order_by(FeatureRun.started_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return {
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": str(item.id),
                "instrument_id": str(item.instrument_id),
                "interval": item.interval,
                "requested_start": _utc(item.requested_start),
                "requested_end": _utc(item.requested_end),
                "feature_version": item.feature_version,
                "configuration_hash": item.configuration_hash,
                "source_classification": item.source_classification,
                "records_received": item.records_received,
                "records_created": item.records_created,
                "records_skipped": item.records_skipped,
                "records_rejected": item.records_rejected,
                "status": item.status,
                "error_category": item.error_category,
                "started_at": _utc(item.started_at),
                "completed_at": _utc(item.completed_at),
            }
            for item in items
        ],
    }


@router.get("/coverage")
def coverage(
    db: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    groups = db.execute(
        select(
            MarketFeature.instrument_id,
            MarketFeature.interval,
            MarketFeature.feature_version,
            MarketFeature.source_classification,
            func.count(),
            func.sum(case((MarketFeature.is_usable.is_(True), 1), else_=0)),
            func.min(MarketFeature.candle_timestamp),
            func.max(MarketFeature.candle_timestamp),
            func.sum(case((MarketFeature.future_return_15m.is_not(None), 1), else_=0)),
            func.sum(case((MarketFeature.future_return_30m.is_not(None), 1), else_=0)),
        )
        .group_by(
            MarketFeature.instrument_id,
            MarketFeature.interval,
            MarketFeature.feature_version,
            MarketFeature.source_classification,
        )
        .order_by(MarketFeature.instrument_id, MarketFeature.feature_version)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "instrument_id": str(row[0]),
                "interval": row[1],
                "feature_version": row[2],
                "source_classification": row[3],
                "total_candles": row[4],
                "usable_rows": row[5],
                "warmup_rows": row[4] - row[5],
                "first_timestamp": _utc(row[6]),
                "last_timestamp": _utc(row[7]),
                "target_15m_rows": row[8],
                "target_30m_rows": row[9],
            }
            for row in groups
        ],
    }


@router.get("/availability")
def availability(
    db: Db,
    instrument_id: uuid.UUID,
    feature_version: str,
) -> dict[str, object]:
    filters = (
        MarketFeature.instrument_id == instrument_id,
        MarketFeature.feature_version == feature_version,
    )
    total = db.scalar(select(func.count()).select_from(MarketFeature).where(*filters)) or 0
    nulls = {
        name: db.scalar(
            select(func.count())
            .select_from(MarketFeature)
            .where(*filters, getattr(MarketFeature, name).is_(None))
        )
        or 0
        for name in (*MODEL_INPUT_FIELDS, *TARGET_FIELDS)
    }
    return {
        "instrument_id": str(instrument_id),
        "feature_version": feature_version,
        "total_rows": total,
        "model_input_null_counts": {name: nulls[name] for name in MODEL_INPUT_FIELDS},
        "target_null_counts": {name: nulls[name] for name in TARGET_FIELDS},
        "invalid_count": 0,
    }


@router.get("/target-distribution")
def target_distribution(
    db: Db,
    instrument_id: uuid.UUID,
    feature_version: str,
) -> dict[str, object]:
    result: dict[str, dict[str, int]] = {}
    for horizon in ("15m", "30m"):
        column = getattr(MarketFeature, f"direction_{horizon}")
        rows = db.execute(
            select(column, func.count())
            .where(
                MarketFeature.instrument_id == instrument_id,
                MarketFeature.feature_version == feature_version,
                column.is_not(None),
            )
            .group_by(column)
        ).all()
        result[horizon] = {
            label: next((count for value, count in rows if value == label), 0)
            for label in ("up", "down", "neutral")
        }
    return {
        "instrument_id": str(instrument_id),
        "feature_version": feature_version,
        "distribution": result,
        "experimental_target": True,
    }


@router.get("/preview")
def feature_preview(
    db: Db,
    instrument_id: uuid.UUID,
    feature_version: str,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    items = list(
        db.scalars(
            select(MarketFeature)
            .where(
                MarketFeature.instrument_id == instrument_id,
                MarketFeature.feature_version == feature_version,
            )
            .order_by(MarketFeature.candle_timestamp)
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return {
        "offset": offset,
        "limit": limit,
        "model_input_fields": list(MODEL_INPUT_FIELDS),
        "target_fields": list(TARGET_FIELDS),
        "items": [
            {
                "candle_timestamp": _utc(item.candle_timestamp),
                "interval": item.interval,
                "feature_version": item.feature_version,
                "source_classification": item.source_classification,
                "is_usable": item.is_usable,
                "model_inputs": {name: getattr(item, name) for name in MODEL_INPUT_FIELDS},
                "targets": {name: getattr(item, name) for name in TARGET_FIELDS},
            }
            for item in items
        ],
        "disclaimer": "Experimental targets only; no model, backtest, or performance claim.",
    }
