import hashlib
import json
import math
import statistics
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.features import FeatureRun, MarketFeature
from app.models.market_data import Instrument, MarketCandle

FEATURE_SET_DEFINITION = {
    "interval": "5m",
    "ema": [9, 21],
    "rsi_wilder": 14,
    "atr_wilder": 14,
    "return_bars": [1, 3, 6],
    "log_std_bars": [12, 36],
    "volume_window": 20,
    "target_bars": [3, 6],
    "target_floor": 0.001,
    "target_atr_multiplier": 0.5,
    "market_timezone": "Asia/Kolkata",
    "session": ["09:15", "15:30"],
}
MODEL_INPUT_FIELDS = (
    "simple_return_1",
    "simple_return_3",
    "simple_return_6",
    "log_return_1",
    "log_return_3",
    "log_return_6",
    "range_close",
    "body_open",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "gap_previous_close",
    "ema_9",
    "ema_21",
    "ema_spread_close",
    "close_distance_ema_9",
    "close_distance_ema_21",
    "ema_9_slope",
    "ema_21_slope",
    "rsi_14",
    "true_range",
    "atr_14",
    "atr_close",
    "log_return_std_12",
    "log_return_std_36",
    "volume_pct_change",
    "volume_mean_20",
    "volume_std_20",
    "volume_zscore",
    "day_of_week",
    "minute_from_open",
    "intraday_sin",
    "intraday_cos",
    "is_opening_session",
    "is_closing_session",
)
TARGET_FIELDS = (
    "target_threshold",
    "future_return_15m",
    "future_return_30m",
    "direction_15m",
    "direction_30m",
)
WARMUP_BARS = 36
IST = ZoneInfo("Asia/Kolkata")


class FeatureEngineeringError(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


@dataclass(frozen=True)
class FeatureRequest:
    instrument_id: uuid.UUID
    interval: str
    start: datetime
    end: datetime
    feature_version: str


@dataclass(frozen=True)
class ComputedFeature:
    candle_timestamp: datetime
    model_inputs: dict[str, float | int | bool | None]
    targets: dict[str, float | str | None]
    is_usable: bool


def configuration_hash(feature_version: str) -> str:
    payload = {"feature_version": feature_version, **FEATURE_SET_DEFINITION}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def normalize_request(request: FeatureRequest, now: datetime | None = None) -> FeatureRequest:
    if request.interval != "FIVE_MINUTE":
        raise FeatureEngineeringError("unsupported-interval")
    if not request.feature_version.strip() or len(request.feature_version) > 80:
        raise FeatureEngineeringError("invalid-feature-version")
    if any(x.tzinfo is None or x.utcoffset() is None for x in (request.start, request.end)):
        raise FeatureEngineeringError("timezone-required")
    start, end = request.start.astimezone(UTC), request.end.astimezone(UTC)
    if start >= end:
        raise FeatureEngineeringError("invalid-range")
    if end > (now or datetime.now(UTC)).astimezone(UTC):
        raise FeatureEngineeringError("future-range")
    return FeatureRequest(
        request.instrument_id, request.interval, start, end, request.feature_version
    )


def _finite(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise FeatureEngineeringError("invalid-candle")
    return number


def validate_candles(candles: list[MarketCandle], request: FeatureRequest) -> str:
    if not candles:
        raise FeatureEngineeringError("no-eligible-candles")
    timestamps: set[datetime] = set()
    sources = {c.is_synthetic for c in candles}
    if len(sources) != 1:
        raise FeatureEngineeringError("mixed-source-classification")
    for candle in candles:
        timestamp = _utc(candle.candle_timestamp)
        if timestamp in timestamps:
            raise FeatureEngineeringError("duplicate-candle-timestamp")
        timestamps.add(timestamp)
        if not request.start <= timestamp < request.end or candle.timeframe != "5m":
            raise FeatureEngineeringError("ineligible-candle")
        o, h, low, close = map(_finite, (candle.open, candle.high, candle.low, candle.close))
        volume = _finite(candle.volume)
        if (
            o <= 0
            or close <= 0
            or min(h, low, volume) < 0
            or h < max(o, close, low)
            or low > min(o, close)
        ):
            raise FeatureEngineeringError("invalid-candle")
    return "synthetic" if True in sources else "genuine"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    result[period - 1] = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for index in range(period, len(values)):
        result[index] = alpha * values[index] + (1 - alpha) * float(result[index - 1])
    return result


def _wilder_rsi(closes: list[float], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain, avg_loss = sum(gains[:period]) / period, sum(losses[:period]) / period

    def score(gain: float, loss: float) -> float:
        if gain == 0 and loss == 0:
            return 50.0
        if loss == 0:
            return 100.0
        return 100 - 100 / (1 + gain / loss)

    result[period] = score(avg_gain, avg_loss)
    for index in range(period + 1, len(closes)):
        avg_gain = ((period - 1) * avg_gain + gains[index - 1]) / period
        avg_loss = ((period - 1) * avg_loss + losses[index - 1]) / period
        result[index] = score(avg_gain, avg_loss)
    return result


def _true_ranges(candles: list[MarketCandle]) -> list[float]:
    result: list[float] = []
    for index, candle in enumerate(candles):
        high, low = float(candle.high), float(candle.low)
        if index == 0:
            result.append(high - low)
        else:
            previous = float(candles[index - 1].close)
            result.append(max(high - low, abs(high - previous), abs(low - previous)))
    return result


def _wilder_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    result[period - 1] = sum(values[:period]) / period
    for index in range(period, len(values)):
        result[index] = (float(result[index - 1]) * (period - 1) + values[index]) / period
    return result


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator != 0 else None


def _return(values: list[float], index: int, bars: int, logarithmic: bool = False) -> float | None:
    if index < bars or values[index - bars] <= 0:
        return None
    ratio = values[index] / values[index - bars]
    if logarithmic:
        return math.log(ratio) if ratio > 0 else None
    return ratio - 1


def _rolling_std(values: list[float | None], index: int, window: int) -> float | None:
    if index + 1 < window:
        return None
    selected = values[index - window + 1 : index + 1]
    if any(value is None for value in selected):
        return None
    return statistics.pstdev(float(value) for value in selected)


def _session_values(timestamp: datetime) -> tuple[int, int, float, float, bool, bool]:
    local = timestamp.astimezone(IST)
    open_minutes = 9 * 60 + 15
    minute = local.hour * 60 + local.minute - open_minutes
    if minute < 0 or minute >= 375:
        raise FeatureEngineeringError("outside-market-session")
    angle = 2 * math.pi * minute / 375
    return local.weekday(), minute, math.sin(angle), math.cos(angle), minute < 30, minute >= 345


def classify_target(future_return: float, threshold: float) -> str:
    if future_return > threshold:
        return "up"
    if future_return < -threshold:
        return "down"
    return "neutral"


def compute_features(candles: list[MarketCandle]) -> list[ComputedFeature]:
    closes = [float(c.close) for c in candles]
    opens = [float(c.open) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    volumes = [float(c.volume) for c in candles]
    ema9, ema21 = _ema(closes, 9), _ema(closes, 21)
    rsi = _wilder_rsi(closes)
    true_ranges = _true_ranges(candles)
    atr = _wilder_average(true_ranges, 14)
    log1 = [_return(closes, index, 1, True) for index in range(len(candles))]
    output: list[ComputedFeature] = []
    timestamps = [_utc(c.candle_timestamp) for c in candles]
    for index, timestamp in enumerate(timestamps):
        previous_close = closes[index - 1] if index else None
        max_body, min_body = max(opens[index], closes[index]), min(opens[index], closes[index])
        volume_window = volumes[index - 19 : index + 1] if index >= 19 else []
        volume_mean = statistics.fmean(volume_window) if volume_window else None
        volume_std = statistics.pstdev(volume_window) if volume_window else None
        previous_volume = volumes[index - 1] if index else None
        volume_change = (
            0.0
            if previous_volume == 0 and volumes[index] == 0
            else _ratio(volumes[index] - previous_volume, previous_volume)
            if previous_volume is not None
            else None
        )
        volume_z = (
            (volumes[index] - float(volume_mean)) / float(volume_std)
            if volume_std not in (None, 0)
            else 0.0
            if volume_std == 0
            else None
        )
        day, minute, sine, cosine, opening, closing = _session_values(timestamp)
        inputs: dict[str, float | int | bool | None] = {
            "simple_return_1": _return(closes, index, 1),
            "simple_return_3": _return(closes, index, 3),
            "simple_return_6": _return(closes, index, 6),
            "log_return_1": log1[index],
            "log_return_3": _return(closes, index, 3, True),
            "log_return_6": _return(closes, index, 6, True),
            "range_close": _ratio(highs[index] - lows[index], closes[index]),
            "body_open": _ratio(closes[index] - opens[index], opens[index]),
            "upper_wick_ratio": _ratio(highs[index] - max_body, closes[index]),
            "lower_wick_ratio": _ratio(min_body - lows[index], closes[index]),
            "gap_previous_close": _ratio(opens[index] - previous_close, previous_close)
            if previous_close is not None
            else None,
            "ema_9": ema9[index],
            "ema_21": ema21[index],
            "ema_spread_close": _ratio(float(ema9[index]) - float(ema21[index]), closes[index])
            if ema9[index] is not None and ema21[index] is not None
            else None,
            "close_distance_ema_9": _ratio(closes[index] - float(ema9[index]), closes[index])
            if ema9[index] is not None
            else None,
            "close_distance_ema_21": _ratio(closes[index] - float(ema21[index]), closes[index])
            if ema21[index] is not None
            else None,
            "ema_9_slope": float(ema9[index]) - float(ema9[index - 1])
            if index and ema9[index] is not None and ema9[index - 1] is not None
            else None,
            "ema_21_slope": float(ema21[index]) - float(ema21[index - 1])
            if index and ema21[index] is not None and ema21[index - 1] is not None
            else None,
            "rsi_14": rsi[index],
            "true_range": true_ranges[index],
            "atr_14": atr[index],
            "atr_close": _ratio(float(atr[index]), closes[index])
            if atr[index] is not None
            else None,
            "log_return_std_12": _rolling_std(log1, index, 12),
            "log_return_std_36": _rolling_std(log1, index, 36),
            "volume_pct_change": volume_change,
            "volume_mean_20": volume_mean,
            "volume_std_20": volume_std,
            "volume_zscore": volume_z,
            "day_of_week": day,
            "minute_from_open": minute,
            "intraday_sin": sine,
            "intraday_cos": cosine,
            "is_opening_session": opening,
            "is_closing_session": closing,
        }
        threshold = (
            max(0.001, 0.5 * float(atr[index]) / closes[index])
            if atr[index] is not None and closes[index] > 0
            else None
        )
        targets: dict[str, float | str | None] = {name: None for name in TARGET_FIELDS}
        targets["target_threshold"] = threshold
        for bars, suffix in ((3, "15m"), (6, "30m")):
            future_index = index + bars
            continuous = future_index < len(candles) and all(
                timestamps[position] - timestamps[position - 1] == timedelta(minutes=5)
                and timestamps[position].astimezone(IST).date() == timestamp.astimezone(IST).date()
                for position in range(index + 1, min(future_index + 1, len(candles)))
            )
            if continuous and threshold is not None and closes[index] > 0:
                future_return = closes[future_index] / closes[index] - 1
                targets[f"future_return_{suffix}"] = future_return
                targets[f"direction_{suffix}"] = classify_target(future_return, threshold)
        usable = all(inputs[name] is not None for name in MODEL_INPUT_FIELDS)
        if any(
            isinstance(value, float) and not math.isfinite(value)
            for value in (*inputs.values(), *targets.values())
        ):
            raise FeatureEngineeringError("non-finite-feature")
        output.append(ComputedFeature(timestamp, inputs, targets, usable))
    return output


def load_eligible_candles(
    session: Session, request: FeatureRequest, now: datetime | None = None
) -> tuple[Instrument, list[MarketCandle], str]:
    instrument = session.get(Instrument, request.instrument_id)
    if instrument is None or not instrument.active:
        raise FeatureEngineeringError("instrument-not-registered")
    completion_cutoff = (now or datetime.now(UTC)).astimezone(UTC) - timedelta(minutes=5)
    candles = list(
        session.scalars(
            select(MarketCandle)
            .where(
                MarketCandle.instrument_id == request.instrument_id,
                MarketCandle.timeframe == "5m",
                MarketCandle.candle_timestamp >= request.start,
                MarketCandle.candle_timestamp < request.end,
                MarketCandle.candle_timestamp <= completion_cutoff,
            )
            .order_by(MarketCandle.candle_timestamp)
        ).all()
    )
    source = validate_candles(candles, request)
    expected_source = "synthetic" if instrument.is_synthetic else "genuine"
    if source != expected_source:
        raise FeatureEngineeringError("instrument-source-classification-mismatch")
    return instrument, candles, source


def preview(
    session: Session, request: FeatureRequest, now: datetime | None = None
) -> dict[str, Any]:
    normalized = normalize_request(request, now)
    _, candles, source = load_eligible_candles(session, normalized, now)
    return {
        "eligible_candles": len(candles),
        "warmup_bars": WARMUP_BARS,
        "expected_target_tail_15m": min(3, len(candles)),
        "expected_target_tail_30m": min(6, len(candles)),
        "source_classification": source,
        "configuration_hash": configuration_hash(normalized.feature_version),
    }


def _failure_audit(
    session: Session,
    request: FeatureRequest,
    config_hash: str,
    source: str,
    received: int,
    category: str,
) -> None:
    session.rollback()
    session.add(
        FeatureRun(
            instrument_id=request.instrument_id,
            interval="5m",
            requested_start=request.start,
            requested_end=request.end,
            feature_version=request.feature_version,
            configuration_hash=config_hash,
            source_classification=source,
            records_received=received,
            records_rejected=received,
            status="failed",
            error_category=category,
            completed_at=datetime.now(UTC),
        )
    )
    session.commit()


def build(session: Session, request: FeatureRequest, now: datetime | None = None) -> FeatureRun:
    normalized = normalize_request(request, now)
    config_hash = configuration_hash(normalized.feature_version)
    source, received = "genuine", 0
    try:
        _, candles, source = load_eligible_candles(session, normalized, now)
        received = len(candles)
        conflict = session.scalar(
            select(MarketFeature)
            .where(
                MarketFeature.instrument_id == normalized.instrument_id,
                MarketFeature.interval == "5m",
                MarketFeature.feature_version == normalized.feature_version,
                MarketFeature.configuration_hash != config_hash,
            )
            .limit(1)
        )
        if conflict:
            raise FeatureEngineeringError("feature-version-configuration-conflict")
        computed = compute_features(candles)
        run = FeatureRun(
            instrument_id=normalized.instrument_id,
            interval="5m",
            requested_start=normalized.start,
            requested_end=normalized.end,
            feature_version=normalized.feature_version,
            configuration_hash=config_hash,
            source_classification=source,
            records_received=received,
            status="running",
        )
        session.add(run)
        session.flush()
        existing = set(
            session.scalars(
                select(MarketFeature.candle_timestamp).where(
                    MarketFeature.instrument_id == normalized.instrument_id,
                    MarketFeature.interval == "5m",
                    MarketFeature.feature_version == normalized.feature_version,
                    MarketFeature.candle_timestamp >= normalized.start,
                    MarketFeature.candle_timestamp < normalized.end,
                )
            ).all()
        )
        for row in computed:
            if row.candle_timestamp in existing:
                run.records_skipped += 1
                continue
            feature = MarketFeature(
                feature_run_id=run.id,
                instrument_id=normalized.instrument_id,
                interval="5m",
                candle_timestamp=row.candle_timestamp,
                feature_version=normalized.feature_version,
                configuration_hash=config_hash,
                source_classification=source,
                is_usable=row.is_usable,
                **row.model_inputs,
                **row.targets,
            )
            try:
                with session.begin_nested():
                    session.add(feature)
                    session.flush()
                run.records_created += 1
            except IntegrityError:
                run.records_skipped += 1
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        session.commit()
        session.refresh(run)
        return run
    except Exception as exc:
        category = (
            exc.category
            if isinstance(exc, FeatureEngineeringError)
            else "database-operation-failure"
            if isinstance(exc, SQLAlchemyError)
            else "feature-computation-failure"
        )
        _failure_audit(session, normalized, config_hash, source, received, category)
        raise FeatureEngineeringError(category) from None
