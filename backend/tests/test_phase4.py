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
from app.main import app
from app.market_data.backfill import execute_backfill, plan_backfill
from app.market_data.cli import main
from app.market_data.historical import HistoricalIngestionError, HistoricalRequest
from app.market_data.provider import CandleRecord, HistoricalBatch
from app.market_data.quality import assess_rows
from app.models.market_data import BackfillChunk, BackfillRun, Instrument, MarketCandle

NOW = datetime(2026, 8, 13, tzinfo=UTC)
START = NOW - timedelta(days=65)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def nifty(session: Session, synthetic: bool = True) -> Instrument:
    item = Instrument(
        provider="fixture" if synthetic else "smartapi",
        exchange="NSE",
        token="99926000",
        trading_symbol="NIFTY 50",
        underlying_symbol="NIFTY",
        instrument_type="spot",
        lot_size=1,
        tick_size=Decimal("0.05"),
        active=True,
        is_synthetic=synthetic,
    )
    session.add(item)
    session.commit()
    return item


def request(item: Instrument, start: datetime = START, end: datetime = NOW) -> HistoricalRequest:
    return HistoricalRequest(item.id, "FIVE_MINUTE", start, end)


class ChunkProvider:
    name = "fixture"
    is_synthetic = True

    def __init__(self, fail_at: int | None = None, empty_at: int | None = None) -> None:
        self.calls: list[tuple[datetime, datetime]] = []
        self.closed = False
        self.fail_at = fail_at
        self.empty_at = empty_at

    def historical_candles(self, instrument, interval, start, end):
        self.calls.append((start, end))
        call = len(self.calls)
        if call == self.fail_at:
            raise RuntimeError("private provider failure")
        if call == self.empty_at:
            return HistoricalBatch(())
        row = CandleRecord(
            instrument.provider,
            instrument.exchange,
            instrument.token,
            "5m",
            start,
            Decimal("100"),
            Decimal("101"),
            Decimal("99"),
            Decimal("100.5"),
            100,
            None,
            "fixture_backfill",
            True,
        )
        return HistoricalBatch((row,))

    def close(self) -> None:
        self.closed = True


def test_exact_chunks_and_newest_sixty_limit() -> None:
    item_id = uuid.uuid4()
    plan = plan_backfill(
        HistoricalRequest(item_id, "FIVE_MINUTE", NOW - timedelta(days=65), NOW), NOW
    )
    assert [chunk.end - chunk.start for chunk in plan.chunks] == [
        timedelta(days=30),
        timedelta(days=30),
        timedelta(days=5),
    ]
    long = plan_backfill(
        HistoricalRequest(item_id, "FIVE_MINUTE", NOW - timedelta(days=2000), NOW), NOW
    )
    assert len(long.chunks) == 60
    assert long.actual_start == long.chunks[0].start
    assert long.chunks[-1].end == NOW


def test_resume_skips_covered_chunks_and_repeat_is_idempotent(session: Session) -> None:
    item = nifty(session)
    first_provider = ChunkProvider()
    first = execute_backfill(session, first_provider, request(item), sleep=lambda _: None, now=NOW)
    second_provider = ChunkProvider()
    second = execute_backfill(
        session, second_provider, request(item), sleep=lambda _: None, now=NOW
    )
    assert first.successful_chunks == 3
    assert second.skipped_chunks == 3 and not second_provider.calls
    assert session.scalar(select(func.count()).select_from(MarketCandle)) == 3
    assert first_provider.closed and second_provider.closed


def test_failure_has_no_retry_preserves_prior_chunk_and_closes(session: Session) -> None:
    item = nifty(session)
    provider = ChunkProvider(fail_at=2)
    with pytest.raises(HistoricalIngestionError, match="provider-or-persistence-failure"):
        execute_backfill(session, provider, request(item), sleep=lambda _: None, now=NOW)
    assert len(provider.calls) == 2 and provider.closed
    assert session.scalar(select(func.count()).select_from(MarketCandle)) == 1
    run = session.scalar(select(BackfillRun))
    assert run and run.status == "failed" and run.failed_chunks == 1
    assert session.scalar(select(func.count()).select_from(BackfillChunk)) == 2


def test_empty_chunk_is_observation_and_not_holiday(session: Session) -> None:
    item = nifty(session)
    run = execute_backfill(
        session, ChunkProvider(empty_at=2), request(item), sleep=lambda _: None, now=NOW
    )
    assert run.empty_chunks == 1 and run.successful_chunks == 3
    assert (
        session.scalar(
            select(func.count()).select_from(BackfillChunk).where(BackfillChunk.status == "empty")
        )
        == 1
    )


def candle(item: Instrument, timestamp: datetime, *, synthetic: bool = False) -> MarketCandle:
    return MarketCandle(
        instrument_id=item.id,
        timeframe="5m",
        candle_timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=100,
        source="fixture" if synthetic else "local_history",
        is_synthetic=synthetic,
    )


def test_quality_complete_partial_gap_monthly_and_separation(session: Session) -> None:
    item = nifty(session, synthetic=False)
    day_one = datetime(2026, 7, 1, 3, 45, tzinfo=UTC)
    rows = [candle(item, day_one + timedelta(minutes=5 * index)) for index in range(75)]
    day_two = datetime(2026, 8, 3, 3, 45, tzinfo=UTC)
    rows += [candle(item, day_two + timedelta(minutes=5 * index)) for index in (0, 1, 3)]
    result = assess_rows(rows)
    assert (result["complete_sessions"], result["partial_sessions"]) == (1, 1)
    assert result["internal_five_minute_gap_count"] == 1
    assert result["longest_contiguous_sequence"] == 75
    assert [month["month"] for month in result["monthly"]] == ["2026-07", "2026-08"]
    assert result["genuine_count"] == 78 and result["synthetic_count"] == 0
    assert result["zero_row_dates_inferred"] is False


@pytest.mark.parametrize(
    "sessions,expected",
    [
        (249, "insufficient"),
        (250, "limited_research_dataset"),
        (499, "limited_research_dataset"),
        (500, "potentially_suitable_for_initial_walk_forward_experiments"),
    ],
)
def test_ml_readiness_thresholds(session: Session, sessions: int, expected: str) -> None:
    item = nifty(session, synthetic=False)
    rows = []
    start = datetime(2020, 1, 1, 3, 45, tzinfo=UTC)
    for day in range(sessions):
        base = start + timedelta(days=day)
        rows.extend(candle(item, base + timedelta(minutes=5 * index)) for index in range(75))
    assert assess_rows(rows)["ml_readiness"] == expected


def test_dry_run_has_zero_calls_and_writes(session: Session, monkeypatch, capsys) -> None:
    item = nifty(session)
    factory = sessionmaker(bind=session.get_bind())
    monkeypatch.setattr("app.market_data.cli.SessionLocal", factory)
    result = main(
        [
            "backfill-history",
            "--provider",
            "fixture",
            "--instrument-id",
            str(item.id),
            "--interval",
            "FIVE_MINUTE",
            "--from",
            START.isoformat(),
            "--to",
            NOW.isoformat(),
            "--dry-run",
        ]
    )
    assert result == 0 and "zero provider calls and zero database writes" in capsys.readouterr().out
    assert session.scalar(select(func.count()).select_from(BackfillRun)) == 0


def test_quality_and_backfill_apis_are_bounded(session: Session) -> None:
    item = nifty(session, synthetic=False)
    session.add(candle(item, datetime(2026, 7, 1, 3, 45, tzinfo=UTC)))
    session.commit()
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            assert (
                client.get(
                    f"/api/market-data/dataset-quality?instrument_id={item.id}&session_limit=101"
                ).status_code
                == 422
            )
            payload = client.get(
                f"/api/market-data/dataset-quality?instrument_id={item.id}&session_limit=1"
            ).json()
            assert payload["total_candles"] == 1 and len(payload["sessions"]) == 1
            assert client.get("/api/market-data/backfill-runs?limit=101").status_code == 422
    finally:
        app.dependency_overrides.clear()
