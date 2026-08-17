import math
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_data import MarketCandle

IST = ZoneInfo("Asia/Kolkata")
SESSION_OPEN = time(9, 15)
SESSION_LAST_START = time(15, 25)
EXPECTED_SESSION_CANDLES = 75


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def assess_rows(
    rows: list[MarketCandle],
    requested_start: datetime | None = None,
    requested_end: datetime | None = None,
) -> dict[str, Any]:
    duplicate_keys = 0
    seen: set[tuple[uuid.UUID, str, datetime, str]] = set()
    invalid = nonfinite = out_of_order = 0
    genuine = synthetic = zero_volume = volume_null = 0
    previous_input: datetime | None = None
    ordered = sorted(rows, key=lambda row: _utc(row.candle_timestamp))
    dates: dict[date, list[datetime]] = defaultdict(list)
    for row in rows:
        timestamp = _utc(row.candle_timestamp)
        key = (row.instrument_id, row.timeframe, timestamp, row.source)
        duplicate_keys += int(key in seen)
        seen.add(key)
        if previous_input is not None and timestamp < previous_input:
            out_of_order += 1
        previous_input = timestamp
        values = (row.open, row.high, row.low, row.close, row.volume)
        if not all(_finite(value) for value in values):
            nonfinite += 1
        else:
            o, high, low, close, volume = map(float, values)
            invalid += int(
                min(o, high, low, close, volume) < 0
                or high < max(o, close, low)
                or low > min(o, close)
            )
        synthetic += int(row.is_synthetic)
        genuine += int(not row.is_synthetic)
        volume_null += int(row.volume is None)
        zero_volume += int(row.volume == 0)
        local = timestamp.astimezone(IST)
        dates[local.date()].append(timestamp)

    sessions: list[dict[str, Any]] = []
    complete = partial = special = internal_gaps = longest = 0
    monthly: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "candles": 0,
            "observed_sessions": 0,
            "complete_sessions": 0,
            "partial_sessions": 0,
        }
    )
    for trading_date in sorted(dates):
        timestamps = sorted(set(dates[trading_date]))
        local_times = [value.astimezone(IST).time().replace(tzinfo=None) for value in timestamps]
        regular = all(SESSION_OPEN <= value <= SESSION_LAST_START for value in local_times)
        expected = [
            datetime.combine(trading_date, SESSION_OPEN, IST) + timedelta(minutes=5 * index)
            for index in range(EXPECTED_SESSION_CANDLES)
        ]
        observed = {value.astimezone(IST) for value in timestamps}
        is_complete = (
            regular and len(observed) == EXPECTED_SESSION_CANDLES and observed == set(expected)
        )
        classification = "complete" if is_complete else "partial" if regular else "non_regular"
        complete += int(is_complete)
        partial += int(classification == "partial")
        special += int(classification == "non_regular")
        sequence = 1 if timestamps else 0
        session_longest = sequence
        gaps = 0
        for index in range(1, len(timestamps)):
            if timestamps[index] - timestamps[index - 1] == timedelta(minutes=5):
                sequence += 1
            else:
                gaps += 1
                sequence = 1
            session_longest = max(session_longest, sequence)
        internal_gaps += gaps
        longest = max(longest, session_longest)
        month = trading_date.strftime("%Y-%m")
        monthly[month]["candles"] += len(timestamps)
        monthly[month]["observed_sessions"] += 1
        monthly[month]["complete_sessions"] += int(is_complete)
        monthly[month]["partial_sessions"] += int(not is_complete)
        sessions.append(
            {
                "date": trading_date.isoformat(),
                "candle_count": len(timestamps),
                "first_timestamp": timestamps[0] if timestamps else None,
                "last_timestamp": timestamps[-1] if timestamps else None,
                "classification": classification,
                "internal_gap_count": gaps,
            }
        )

    years = {item["date"][:4] for item in sessions if item["classification"] == "complete"}
    prerequisites = (
        duplicate_keys == 0 and invalid == 0 and nonfinite == 0 and not (genuine and synthetic)
    )
    if complete >= 500 and len(years) >= 2 and prerequisites:
        readiness = "potentially_suitable_for_initial_walk_forward_experiments"
    elif complete >= 250 and prerequisites:
        readiness = "limited_research_dataset"
    else:
        readiness = "insufficient"
    return {
        "requested_start": requested_start,
        "requested_end": requested_end,
        "observed_start": ordered[0].candle_timestamp if ordered else None,
        "observed_end": ordered[-1].candle_timestamp if ordered else None,
        "total_candles": len(rows),
        "observed_trading_dates": len(dates),
        "genuine_count": genuine,
        "synthetic_count": synthetic,
        "duplicate_key_count": duplicate_keys,
        "invalid_ohlcv_count": invalid,
        "non_finite_count": nonfinite,
        "out_of_order_count": out_of_order,
        "internal_five_minute_gap_count": internal_gaps,
        "longest_contiguous_sequence": longest,
        "volume_null_count": volume_null,
        "zero_volume_count": zero_volume,
        "complete_sessions": complete,
        "partial_sessions": partial,
        "non_regular_sessions": special,
        "sessions": sessions,
        "monthly": [{"month": month, **monthly[month]} for month in sorted(monthly)],
        "ml_readiness": readiness,
        "regular_session_assumption": (
            "Asia/Kolkata 09:15-15:30; 75 five-minute starts through 15:25; "
            "not an official exchange calendar"
        ),
        "zero_row_dates_inferred": False,
        "predictability_or_profitability_proven": False,
    }


def dataset_quality(
    session: Session,
    instrument_id: uuid.UUID,
    *,
    requested_start: datetime | None = None,
    requested_end: datetime | None = None,
) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(MarketCandle)
            .where(MarketCandle.instrument_id == instrument_id, MarketCandle.timeframe == "5m")
            .order_by(MarketCandle.candle_timestamp)
        ).all()
    )
    return assess_rows(rows, requested_start, requested_end)
