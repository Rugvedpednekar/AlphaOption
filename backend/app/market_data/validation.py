from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.market_data.provider import CandleRecord

TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "1d"}


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("malformed candle timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("candle timestamp must include a timezone")
    return parsed.astimezone(UTC)


def market_time_to_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("malformed market timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    return parsed.astimezone(UTC)


def decimal_value(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if not result.is_finite():
        raise ValueError(f"invalid {field}")
    return result


def validate_candle(record: CandleRecord) -> CandleRecord:
    if record.timeframe not in TIMEFRAMES:
        raise ValueError("unsupported timeframe")
    if (
        not isinstance(record.candle_timestamp, datetime)
        or record.candle_timestamp.tzinfo is None
        or record.candle_timestamp.utcoffset() is None
    ):
        raise ValueError("candle timestamp must be timezone-aware")
    if not all(value.is_finite() for value in (record.open, record.high, record.low, record.close)):
        raise ValueError("prices must be finite")
    if min(record.open, record.high, record.low, record.close) < 0:
        raise ValueError("prices cannot be negative")
    if record.high < max(record.open, record.close, record.low) or record.low > min(
        record.open, record.close, record.high
    ):
        raise ValueError("impossible OHLC relationship")
    if record.volume < 0 or (record.open_interest is not None and record.open_interest < 0):
        raise ValueError("volume and open interest cannot be negative")
    return record
