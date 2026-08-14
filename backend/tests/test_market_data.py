from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.market_data import _raw_gap_count
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.market_data.fixture_provider import FixtureProvider
from app.market_data.ingestion import ingest_provider
from app.market_data.provider import CandleRecord
from app.market_data.validation import market_time_to_utc, parse_timestamp, validate_candle
from app.models.market_data import IngestionRun, Instrument, MarketCandle


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def test_fixture_ingestion_is_idempotent(session: Session) -> None:
    first = ingest_provider(session, FixtureProvider())
    second = ingest_provider(session, FixtureProvider())
    assert first.records_inserted == 8
    assert second.records_inserted == 0
    assert session.scalar(select(func.count()).select_from(Instrument)) == 4
    assert session.scalar(select(func.count()).select_from(MarketCandle)) == 4
    assert session.scalar(select(func.count()).select_from(IngestionRun)) == 2


def test_market_timestamp_converts_to_utc() -> None:
    assert market_time_to_utc("2026-08-13T09:15:00") == datetime(2026, 8, 13, 3, 45, tzinfo=UTC)
    assert parse_timestamp("2026-08-13T09:15:00+05:30").hour == 3
    with pytest.raises(ValueError, match="timezone"):
        parse_timestamp("2026-08-13T09:15:00")


def candle() -> CandleRecord:
    return CandleRecord(
        "fixture",
        "NSE",
        "token",
        "1m",
        datetime.now(UTC),
        Decimal("10"),
        Decimal("12"),
        Decimal("9"),
        Decimal("11"),
        1,
        None,
        "test",
        True,
    )


@pytest.mark.parametrize(
    "bad",
    [
        replace(candle(), high=Decimal("8")),
        replace(candle(), volume=-1),
        replace(candle(), open=Decimal("-1")),
    ],
)
def test_invalid_candles_are_rejected(bad: CandleRecord) -> None:
    with pytest.raises(ValueError):
        validate_candle(bad)


def test_model_constraints_exist() -> None:
    names = {constraint.name for constraint in MarketCandle.__table__.constraints}
    assert {"uq_market_candle_identity", "ck_candle_ohlc", "ck_candle_volume_nonnegative"} <= names


def test_market_data_api_pagination_and_validation(session: Session) -> None:
    ingest_provider(session, FixtureProvider())
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            coverage = client.get("/api/market-data/coverage")
            assert coverage.status_code == 200
            assert coverage.json()["contains_synthetic_data"] is True
            assert coverage.json()["instruments_stored"] == 4
            assert coverage.json()["candle_count"] == 4
            assert coverage.json()["coverage"][0]["raw_gap_count"] == 0
            assert "trading_symbol" not in coverage.json()["coverage"][0]
            assert coverage.json()["gap_method"] == "raw_interval_slots"
            assert client.get("/api/market-data/coverage?limit=201").status_code == 422
            gaps = client.get("/api/market-data/gaps?limit=1")
            assert gaps.status_code == 200
            assert len(gaps.json()["items"]) == 1
            assert gaps.json()["items"][0]["gap_method"] == "raw_interval_slots"
            assert client.get("/api/market-data/gaps?limit=201").status_code == 422
            assert client.get("/api/market-data/instruments?limit=201").status_code == 422
            instrument_payload = client.get("/api/market-data/instruments?limit=1").json()
            assert "token" not in instrument_payload["items"][0]
            assert "trading_symbol" not in instrument_payload["items"][0]
            assert "underlying_symbol" not in instrument_payload["items"][0]
            instrument_id = instrument_payload["items"][0]["id"]
            assert (
                client.get(
                    f"/api/market-data/instruments/{instrument_id}/candles?timeframe=2m"
                ).status_code
                == 422
            )
            assert client.get("/api/market-data/ingestion-runs?limit=101").status_code == 422
            assert coverage.json()["earliest_candle_timestamp"].endswith(("Z", "+00:00"))
    finally:
        app.dependency_overrides.clear()


def test_raw_gap_count_includes_closed_market_periods() -> None:
    friday = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
    monday = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    assert _raw_gap_count(2, friday, monday, "1m") == 4319


def test_duplicate_counter_has_matching_orm_and_server_defaults() -> None:
    column = IngestionRun.__table__.c.records_duplicates
    assert column.default is not None and column.default.arg == 0
    assert column.server_default is not None and str(column.server_default.arg) == "0"
