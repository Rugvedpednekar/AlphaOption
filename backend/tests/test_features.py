import math
import statistics
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.features.cli import main as feature_cli
from app.features.engine import (
    MODEL_INPUT_FIELDS,
    TARGET_FIELDS,
    FeatureEngineeringError,
    FeatureRequest,
    _ema,
    _rolling_std,
    _session_values,
    _true_ranges,
    _wilder_average,
    _wilder_rsi,
    build,
    classify_target,
    compute_features,
    configuration_hash,
    load_eligible_candles,
    normalize_request,
    validate_candles,
)
from app.main import app
from app.models.features import FeatureRun, MarketFeature
from app.models.market_data import Instrument, MarketCandle

START = datetime(2026, 7, 1, 3, 45, tzinfo=UTC)
NOW = datetime(2026, 8, 13, tzinfo=UTC)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def instrument(session: Session, synthetic: bool = False) -> Instrument:
    value = Instrument(
        provider="fixture" if synthetic else "local",
        exchange="NSE",
        token=str(uuid.uuid4()),
        trading_symbol="INDEX",
        underlying_symbol="INDEX",
        instrument_type="spot",
        expiry=None,
        strike=None,
        option_type=None,
        lot_size=1,
        tick_size=Decimal("0.05"),
        active=True,
        is_synthetic=synthetic,
    )
    session.add(value)
    session.flush()
    return value


def candles_for(
    item: Instrument,
    count: int = 50,
    *,
    start: datetime = START,
    synthetic: bool | None = None,
    gap_after: int | None = None,
    constant_volume: bool = False,
) -> list[MarketCandle]:
    result = []
    cursor = start
    for index in range(count):
        if gap_after is not None and index == gap_after + 1:
            cursor += timedelta(minutes=5)
        close = Decimal("100") + Decimal(index) / 10
        result.append(
            MarketCandle(
                instrument_id=item.id,
                timeframe="5m",
                candle_timestamp=cursor,
                open=close - Decimal("0.1"),
                high=close + Decimal("0.5"),
                low=close - Decimal("0.5"),
                close=close,
                volume=0 if constant_volume else 100 + index,
                open_interest=None,
                source="fixture"
                if (item.is_synthetic if synthetic is None else synthetic)
                else "local_history",
                is_synthetic=item.is_synthetic if synthetic is None else synthetic,
            )
        )
        cursor += timedelta(minutes=5)
    return result


def request(item: Instrument, count: int = 50, version: str = "v1") -> FeatureRequest:
    return FeatureRequest(
        item.id, "FIVE_MINUTE", START, START + timedelta(minutes=5 * count), version
    )


def test_exact_ema_and_wilder_calculations() -> None:
    values = [float(value) for value in range(1, 13)]
    ema = _ema(values, 3)
    assert ema[:2] == [None, None]
    assert ema[2:6] == pytest.approx([2, 3, 4, 5])
    rsi = _wilder_rsi(values, 3)
    assert rsi[3:] == pytest.approx([100] * 9)
    atr = _wilder_average([2.0] * 20, 14)
    assert atr[13:] == pytest.approx([2.0] * 7)

    flat_rsi = _wilder_rsi([10.0] * 18, 14)
    assert flat_rsi[14:] == pytest.approx([50.0] * 4)
    falling_rsi = _wilder_rsi([float(value) for value in range(18, 0, -1)], 14)
    assert falling_rsi[14:] == pytest.approx([0.0] * 4)


def test_true_range_population_std_and_session_cycle(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item, 3)
    values[1].high = Decimal("102")
    values[1].low = Decimal("100.5")
    assert _true_ranges(values) == pytest.approx([1.0, 2.0, 1.0])
    assert _rolling_std([1.0, 2.0, 3.0], 2, 3) == pytest.approx(statistics.pstdev([1.0, 2.0, 3.0]))
    day, minute, sine, cosine, _, _ = _session_values(START)
    assert (day, minute, sine, cosine) == pytest.approx((2, 0, 0, 1))
    _, minute, sine, cosine, _, closing = _session_values(datetime(2026, 7, 1, 9, 55, tzinfo=UTC))
    assert minute == 370
    assert sine == pytest.approx(math.sin(2 * math.pi * 370 / 375))
    assert cosine == pytest.approx(math.cos(2 * math.pi * 370 / 375))
    assert closing


def test_returns_windows_warmup_and_feature_target_separation(session: Session) -> None:
    item = instrument(session)
    candles = candles_for(item)
    rows = compute_features(candles)
    assert rows[0].model_inputs["simple_return_1"] is None
    assert rows[6].model_inputs["simple_return_6"] == pytest.approx(0.006)
    assert rows[36].model_inputs["log_return_std_36"] is not None
    assert not rows[35].is_usable and rows[36].is_usable
    assert set(rows[40].model_inputs) == set(MODEL_INPUT_FIELDS)
    assert set(rows[40].targets) == set(TARGET_FIELDS)
    assert not set(MODEL_INPUT_FIELDS) & set(TARGET_FIELDS)


def test_leakage_regression_future_changes_do_not_change_inputs(session: Session) -> None:
    item = instrument(session)
    original = candles_for(item)
    changed = candles_for(item)
    for candle in changed[26:]:
        candle.close += Decimal("50")
        candle.high += Decimal("50")
    before, after = compute_features(original), compute_features(changed)
    assert [row.model_inputs for row in before[:26]] == [row.model_inputs for row in after[:26]]


def test_zero_volume_and_zero_variance_are_finite(session: Session) -> None:
    item = instrument(session)
    rows = compute_features(candles_for(item, constant_volume=True))
    assert rows[20].model_inputs["volume_pct_change"] == 0
    assert rows[20].model_inputs["volume_std_20"] == 0
    assert rows[20].model_inputs["volume_zscore"] == 0
    assert all(
        not isinstance(value, float) or math.isfinite(value)
        for row in rows
        for value in row.model_inputs.values()
        if value is not None
    )


def test_invalid_nonfinite_and_mixed_sources_rejected(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item, 3)
    values[1].close = Decimal("NaN")
    with pytest.raises(FeatureEngineeringError, match="invalid-candle"):
        validate_candles(values, request(item, 3))

    values = candles_for(item, 3)
    values[1].open = Decimal("0")
    with pytest.raises(FeatureEngineeringError, match="invalid-candle"):
        validate_candles(values, request(item, 3))


def test_duplicate_input_timestamp_is_rejected(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item, 3)
    values[2].candle_timestamp = values[1].candle_timestamp
    with pytest.raises(FeatureEngineeringError, match="duplicate-candle-timestamp"):
        validate_candles(values, request(item, 3))

    values = candles_for(item, 3)
    values[1].is_synthetic = True
    with pytest.raises(FeatureEngineeringError, match="mixed-source-classification"):
        validate_candles(values, request(item, 3))


def test_instrument_and_candle_source_classification_must_match(session: Session) -> None:
    item = instrument(session)
    session.add_all(candles_for(item, synthetic=True))
    session.commit()
    with pytest.raises(FeatureEngineeringError, match="instrument-source-classification-mismatch"):
        load_eligible_candles(session, request(item), NOW)


def test_session_conversion_and_closed_candle_policy(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item, 2)
    session.add_all(values)
    session.commit()
    req = request(item, 2)
    _, eligible, _ = load_eligible_candles(session, req, START + timedelta(minutes=9))
    assert len(eligible) == 1
    row = compute_features(values)[0]
    assert row.model_inputs["day_of_week"] == 2
    assert row.model_inputs["minute_from_open"] == 0
    assert row.model_inputs["is_opening_session"] is True


def test_targets_align_and_tail_is_unavailable(session: Session) -> None:
    item = instrument(session)
    rows = compute_features(candles_for(item, 50))
    expected_15 = 103 / 100 - 1
    expected_30 = 106 / 100 - 1
    assert rows[0].targets["future_return_15m"] is None  # threshold warm-up
    assert rows[20].targets["future_return_15m"] == pytest.approx((102.3 / 102) - 1)
    assert rows[20].targets["future_return_30m"] == pytest.approx((102.6 / 102) - 1)
    assert rows[-3].targets["future_return_15m"] is None
    assert rows[-6].targets["future_return_30m"] is None
    assert expected_15 > 0 and expected_30 > 0


def test_targets_do_not_cross_gap_or_trading_date(session: Session) -> None:
    item = instrument(session)
    gap_rows = compute_features(candles_for(item, 45, gap_after=39))
    assert gap_rows[38].targets["future_return_15m"] is None
    day_one = candles_for(item, 40, start=datetime(2026, 7, 1, 6, 10, tzinfo=UTC))
    day_two = candles_for(item, 4, start=datetime(2026, 7, 2, 3, 45, tzinfo=UTC))
    date_rows = compute_features(day_one + day_two)
    assert date_rows[38].targets["future_return_15m"] is None


def test_return_and_candle_shape_alignment(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item, 8)
    values[6].open = Decimal("100")
    values[6].high = Decimal("103")
    values[6].low = Decimal("99")
    values[6].close = Decimal("102")
    rows = compute_features(values)
    inputs = rows[6].model_inputs
    assert inputs["simple_return_1"] == pytest.approx(102 / 100.5 - 1)
    assert inputs["simple_return_3"] == pytest.approx(102 / 100.3 - 1)
    assert inputs["simple_return_6"] == pytest.approx(102 / 100 - 1)
    assert inputs["range_close"] == pytest.approx(4 / 102)
    assert inputs["body_open"] == pytest.approx(2 / 100)
    assert inputs["upper_wick_ratio"] == pytest.approx(1 / 102)
    assert inputs["lower_wick_ratio"] == pytest.approx(1 / 102)


def test_positive_volume_after_zero_is_unavailable_not_infinite(session: Session) -> None:
    item = instrument(session)
    values = candles_for(item)
    values[19].volume = 0
    values[20].volume = 100
    rows = compute_features(values)
    assert rows[20].model_inputs["volume_pct_change"] is None


def test_threshold_and_three_target_classes(session: Session) -> None:
    item = instrument(session)
    rows = compute_features(candles_for(item, 50))
    threshold = rows[20].targets["target_threshold"]
    assert threshold is not None and threshold >= 0.001
    assert classify_target(0.002, 0.001) == "up"
    assert classify_target(-0.002, 0.001) == "down"
    assert classify_target(0.001, 0.001) == "neutral"


def test_idempotent_build_and_configuration_hash(session: Session) -> None:
    item = instrument(session)
    session.add_all(candles_for(item))
    session.commit()
    first = build(session, request(item), NOW)
    second = build(session, request(item), NOW)
    assert (first.records_created, first.records_skipped) == (50, 0)
    assert (second.records_created, second.records_skipped) == (0, 50)
    assert session.scalar(select(func.count()).select_from(MarketFeature)) == 50
    assert len(configuration_hash("v1")) == 64


def test_cli_dry_run_has_zero_writes(session: Session, monkeypatch, capsys) -> None:
    item = instrument(session)
    session.add_all(candles_for(item))
    session.commit()
    factory = sessionmaker(bind=session.get_bind())
    monkeypatch.setattr("app.features.cli.SessionLocal", factory)
    result = feature_cli(
        [
            "build",
            "--instrument-id",
            str(item.id),
            "--interval",
            "FIVE_MINUTE",
            "--from",
            START.isoformat(),
            "--to",
            (START + timedelta(minutes=250)).isoformat(),
            "--feature-version",
            "v1",
            "--dry-run",
        ]
    )
    assert result == 0
    assert "zero database writes and zero provider calls" in capsys.readouterr().out
    with factory() as check:
        assert check.scalar(select(func.count()).select_from(FeatureRun)) == 0
        assert check.scalar(select(func.count()).select_from(MarketFeature)) == 0


def test_version_configuration_conflict_is_audited(session: Session, monkeypatch) -> None:
    item = instrument(session)
    session.add_all(candles_for(item))
    session.commit()
    build(session, request(item), NOW)
    monkeypatch.setattr("app.features.engine.configuration_hash", lambda _: "0" * 64)
    with pytest.raises(FeatureEngineeringError, match="feature-version-configuration-conflict"):
        build(session, request(item), NOW)
    failed = session.scalar(select(FeatureRun).where(FeatureRun.status == "failed"))
    assert failed and failed.error_category == "feature-version-configuration-conflict"


def test_bounded_feature_apis_and_separation(session: Session) -> None:
    item = instrument(session, synthetic=True)
    session.add_all(candles_for(item))
    session.commit()
    build(session, request(item), NOW)
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            assert client.get("/api/features/runs?limit=101").status_code == 422
            assert client.get("/api/features/coverage?limit=101").status_code == 422
            coverage = client.get("/api/features/coverage").json()["items"][0]
            assert coverage["source_classification"] == "synthetic"
            params = f"instrument_id={item.id}&feature_version=v1"
            preview_payload = client.get(f"/api/features/preview?{params}&limit=1").json()
            assert set(preview_payload["items"][0]["model_inputs"]) == set(MODEL_INPUT_FIELDS)
            assert set(preview_payload["items"][0]["targets"]) == set(TARGET_FIELDS)
            assert client.get(f"/api/features/preview?{params}&limit=101").status_code == 422
            assert client.get(f"/api/features/availability?{params}").status_code == 200
            assert client.get(f"/api/features/target-distribution?{params}").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_request_validation() -> None:
    identifier = uuid.uuid4()
    with pytest.raises(FeatureEngineeringError, match="unsupported-interval"):
        normalize_request(
            FeatureRequest(identifier, "ONE_MINUTE", START, START + timedelta(hours=1), "v1"), NOW
        )
    with pytest.raises(FeatureEngineeringError, match="timezone-required"):
        normalize_request(
            FeatureRequest(
                identifier,
                "FIVE_MINUTE",
                START.replace(tzinfo=None),
                START + timedelta(hours=1),
                "v1",
            ),
            NOW,
        )
