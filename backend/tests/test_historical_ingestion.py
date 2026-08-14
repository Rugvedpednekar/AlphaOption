import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.market_data.cli import main
from app.market_data.historical import (
    HistoricalIngestionError,
    HistoricalRequest,
    _store_candle,
    build_chunks,
    ingest_history,
    normalize_request,
)
from app.market_data.historical_providers import (
    FixtureHistoricalProvider,
    SmartApiHistoricalProvider,
    validate_nifty_identity,
)
from app.market_data.provider import CandleRecord, HistoricalBatch, InstrumentRecord
from app.models.market_data import IngestionRun, Instrument, MarketCandle

NOW = datetime(2026, 8, 13, tzinfo=UTC)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def registered(session: Session) -> Instrument:
    value = Instrument(
        provider="fixture",
        exchange="NSE",
        token="safe-fixture-token",
        trading_symbol="NIFTY 50",
        underlying_symbol="NIFTY",
        instrument_type="spot",
        expiry=None,
        strike=None,
        option_type=None,
        lot_size=1,
        tick_size=Decimal("0.05"),
        active=True,
        is_synthetic=True,
    )
    session.add(value)
    session.commit()
    return value


def request(
    instrument: Instrument, start: datetime = NOW - timedelta(hours=1), end: datetime = NOW
) -> HistoricalRequest:
    return HistoricalRequest(instrument.id, "FIVE_MINUTE", start, end)


@pytest.mark.parametrize(
    "start,end,category",
    [
        (NOW, NOW, "invalid-range"),
        (NOW, NOW - timedelta(days=1), "invalid-range"),
        (NOW, NOW + timedelta(minutes=1), "future-range"),
        (NOW - timedelta(days=367), NOW, "range-too-large"),
    ],
)
def test_invalid_ranges(start: datetime, end: datetime, category: str) -> None:
    with pytest.raises(HistoricalIngestionError, match=category):
        normalize_request(HistoricalRequest(uuid.uuid4(), "ONE_MINUTE", start, end), NOW)


def test_utc_normalization_and_interval_specific_chunks() -> None:
    start = datetime.fromisoformat("2026-01-01T05:30:00+05:30")
    normalized = normalize_request(
        HistoricalRequest(uuid.uuid4(), "ONE_MINUTE", start, start + timedelta(days=65)), NOW
    )
    chunks = build_chunks(normalized)
    assert normalized.start == datetime(2026, 1, 1, tzinfo=UTC)
    assert [(x.end - x.start).days for x in chunks] == [7] * 9 + [2]
    assert all(chunks[index].end == chunks[index + 1].start for index in range(len(chunks) - 1))
    five_minute = replace(normalized, interval="FIVE_MINUTE")
    assert [(x.end - x.start).days for x in build_chunks(five_minute)] == [30, 30, 5]


@pytest.mark.parametrize("interval,days", [("ONE_MINUTE", 7), ("FIVE_MINUTE", 30)])
def test_exact_and_partial_chunk_boundaries(interval: str, days: int) -> None:
    request_value = HistoricalRequest(
        uuid.uuid4(), interval, NOW - timedelta(days=days, minutes=5), NOW
    )
    chunks = build_chunks(request_value)
    assert len(chunks) == 2
    assert chunks[0].end == chunks[1].start
    assert chunks[0].end - chunks[0].start == timedelta(days=days)
    assert chunks[1].end - chunks[1].start == timedelta(minutes=5)


def test_chunks_remain_contiguous_across_timezone_offset_transition() -> None:
    start = datetime.fromisoformat("2026-03-07T01:30:00-05:00")
    end = datetime.fromisoformat("2026-03-15T01:30:00-04:00")
    normalized = normalize_request(HistoricalRequest(uuid.uuid4(), "ONE_MINUTE", start, end), NOW)
    chunks = build_chunks(normalized)
    assert all(chunk.start.tzinfo is UTC and chunk.end.tzinfo is UTC for chunk in chunks)
    assert chunks[0].end == chunks[1].start
    assert chunks[-1].end == normalized.end


def test_fixture_is_repeat_safe_and_audited(session: Session) -> None:
    instrument = registered(session)
    first = ingest_history(session, FixtureHistoricalProvider(), request(instrument), now=NOW)
    second = ingest_history(session, FixtureHistoricalProvider(), request(instrument), now=NOW)
    assert (first.records_inserted, second.records_inserted) == (12, 0)
    assert second.records_duplicates == 12
    assert session.scalar(select(func.count()).select_from(MarketCandle)) == 12
    assert session.scalar(select(func.count()).select_from(IngestionRun)) == 2


class RecordingProvider(FixtureHistoricalProvider):
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, datetime]] = []
        self.closed = False

    def historical_candles(self, instrument, interval, start, end):
        self.calls.append((start, end))
        batch = super().historical_candles(
            instrument, interval, start, min(end, start + timedelta(minutes=5))
        )
        return batch

    def close(self) -> None:
        self.closed = True


def test_calls_are_sequential_throttled_and_closed(session: Session) -> None:
    instrument = registered(session)
    provider = RecordingProvider()
    sleeps: list[float] = []
    long_request = request(instrument, NOW - timedelta(days=65), NOW)
    ingest_history(
        session, provider, long_request, throttle_seconds=0.25, sleep=sleeps.append, now=NOW
    )
    assert len(provider.calls) == 3
    assert sleeps == [0.25, 0.25]
    assert provider.closed


class InvalidProvider(RecordingProvider):
    def historical_candles(self, instrument, interval, start, end):
        batch = super().historical_candles(instrument, interval, start, end)
        valid = batch.rows[0]
        return HistoricalBatch(
            (
                valid,
                replace(valid, volume=-1),
                replace(valid, open=Decimal("NaN")),
                replace(valid, high=Decimal("1")),
                replace(valid, token="conflict"),
            )
        )


def test_invalid_duplicate_and_metadata_conflicts_are_rejected(session: Session) -> None:
    instrument = registered(session)
    run = ingest_history(session, InvalidProvider(), request(instrument), now=NOW)
    assert run.records_inserted == 1
    assert run.records_rejected == 4
    assert (
        run.records_received == run.records_inserted + run.records_duplicates + run.records_rejected
    )
    assert run.status == "completed_with_rejections"
    assert "candle-validation-rejected" in (run.error_summary or "")


class FailingProvider(RecordingProvider):
    def historical_candles(self, instrument, interval, start, end):
        raise RuntimeError("raw provider details must not escape")


class PartialProvider(RecordingProvider):
    def historical_candles(self, instrument, interval, start, end):
        batch = super().historical_candles(instrument, interval, start, end)
        return HistoricalBatch(batch.rows, complete=False)


def test_failure_is_sanitized_audited_and_session_closed(session: Session) -> None:
    instrument = registered(session)
    provider = FailingProvider()
    with pytest.raises(HistoricalIngestionError, match="provider-or-persistence-failure"):
        ingest_history(session, provider, request(instrument), now=NOW)
    run = session.scalar(select(IngestionRun))
    assert run and run.status == "failed" and run.error_summary == "provider-or-persistence-failure"
    assert provider.closed


class FailFirstDatabaseRead:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.failed = False

    def get(self, *args, **kwargs):
        if not self.failed:
            self.failed = True
            raise SQLAlchemyError("private database connection detail")
        return self.session.get(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self.session, name)


def test_database_connection_failure_is_sanitized_and_audited(session: Session) -> None:
    instrument = registered(session)
    provider = RecordingProvider()
    with pytest.raises(HistoricalIngestionError, match="database-connection-failure"):
        ingest_history(FailFirstDatabaseRead(session), provider, request(instrument), now=NOW)
    run = session.scalar(select(IngestionRun))
    assert run and run.status == "failed"
    assert run.error_summary == "database-connection-failure"
    assert "private" not in (run.error_summary or "")
    assert provider.closed


def test_partial_provider_response_rolls_back_and_is_audited(session: Session) -> None:
    instrument = registered(session)
    provider = PartialProvider()
    with pytest.raises(HistoricalIngestionError, match="incomplete-provider-response"):
        ingest_history(session, provider, request(instrument), now=NOW)
    run = session.scalar(select(IngestionRun))
    assert run and run.status == "failed"
    assert run.error_summary == "incomplete-provider-response"
    assert run.records_received == 1 and run.records_rejected == 1
    assert session.scalar(select(func.count()).select_from(MarketCandle)) == 0
    assert provider.closed


class OutOfRangeProvider(RecordingProvider):
    def historical_candles(self, instrument, interval, start, end):
        batch = super().historical_candles(instrument, interval, start, end)
        return HistoricalBatch((replace(batch.rows[0], candle_timestamp=end),))


def test_out_of_range_timestamp_is_rejected(session: Session) -> None:
    instrument = registered(session)
    run = ingest_history(session, OutOfRangeProvider(), request(instrument), now=NOW)
    assert (run.records_received, run.records_inserted, run.records_rejected) == (1, 0, 1)
    assert run.status == "completed_with_rejections"


class DuplicateResponseProvider(RecordingProvider):
    def historical_candles(self, instrument, interval, start, end):
        batch = super().historical_candles(instrument, interval, start, end)
        return HistoricalBatch((batch.rows[0], batch.rows[0]))


def test_duplicate_timestamp_inside_response_is_rejected(session: Session) -> None:
    instrument = registered(session)
    run = ingest_history(session, DuplicateResponseProvider(), request(instrument), now=NOW)
    assert (run.records_received, run.records_inserted, run.records_duplicates) == (2, 1, 0)
    assert run.records_rejected == 1
    assert run.records_received == run.records_inserted + run.records_rejected


class FailFirstCommitSession(Session):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commit_attempts = 0

    def commit(self) -> None:
        self.commit_attempts += 1
        if self.commit_attempts == 1:
            raise RuntimeError("commit failed with private details")
        super().commit()


def test_success_commit_failure_rolls_back_candles_and_persists_failure_audit() -> None:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with FailFirstCommitSession(engine) as value:
        instrument = Instrument(
            provider="fixture",
            exchange="NSE",
            token="commit-failure-token",
            trading_symbol="NIFTY 50",
            underlying_symbol="NIFTY",
            instrument_type="spot",
            expiry=None,
            strike=None,
            option_type=None,
            lot_size=1,
            tick_size=Decimal("0.05"),
            active=True,
            is_synthetic=True,
        )
        value.add(instrument)
        value.flush()
        request_value = request(instrument)
        with pytest.raises(HistoricalIngestionError, match="provider-or-persistence-failure"):
            ingest_history(value, FixtureHistoricalProvider(), request_value, now=NOW)
        run = value.scalar(select(IngestionRun))
        assert run and run.status == "failed" and run.completed_at is not None
        assert value.scalar(select(func.count()).select_from(MarketCandle)) == 0


def test_zero_prices_and_zero_volume_are_valid(session: Session) -> None:
    instrument = registered(session)
    row = CandleRecord(
        instrument.provider,
        instrument.exchange,
        instrument.token,
        "5m",
        NOW - timedelta(minutes=5),
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
        0,
        0,
        "zero_fixture",
        True,
    )
    result, _ = _store_candle(session, instrument, row, "5m", NOW - timedelta(minutes=10), NOW)
    assert result == "inserted"


class ScalarRaceSession:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.scalar_calls = 0

    def scalar(self, query):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return None
        return self.session.scalar(query)

    def __getattr__(self, name: str):
        return getattr(self.session, name)


def test_uniqueness_race_is_classified_as_duplicate(session: Session) -> None:
    instrument = registered(session)
    row = (
        FixtureHistoricalProvider()
        .historical_candles(
            InstrumentRecord(
                instrument.provider,
                instrument.exchange,
                instrument.token,
                instrument.trading_symbol,
                instrument.underlying_symbol,
                instrument.instrument_type,
                instrument.expiry,
                instrument.strike,
                instrument.option_type,
                instrument.lot_size,
                instrument.tick_size,
                instrument.active,
                instrument.is_synthetic,
            ),
            "FIVE_MINUTE",
            NOW - timedelta(minutes=5),
            NOW,
        )
        .rows[0]
    )
    _store_candle(session, instrument, row, "5m", NOW - timedelta(minutes=5), NOW)
    session.flush()
    result, _ = _store_candle(
        ScalarRaceSession(session), instrument, row, "5m", NOW - timedelta(minutes=5), NOW
    )
    assert result == "duplicate"


def test_dry_run_uses_no_database_or_provider(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("app.market_data.cli.SessionLocal", lambda: pytest.fail("database opened"))
    code = main(
        [
            "ingest-history",
            "--provider",
            "fixture",
            "--instrument-id",
            str(uuid.uuid4()),
            "--interval",
            "ONE_MINUTE",
            "--from",
            "2026-01-01T00:00:00Z",
            "--to",
            "2026-01-01T00:10:00Z",
            "--dry-run",
        ]
    )
    assert code == 0
    assert "zero provider calls and zero database writes" in capsys.readouterr().out


def test_smartapi_requires_acknowledgement(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "ingest-history",
            "--provider",
            "smartapi",
            "--instrument-id",
            str(uuid.uuid4()),
            "--interval",
            "ONE_MINUTE",
            "--from",
            "2026-01-01T00:00:00Z",
            "--to",
            "2026-01-01T00:10:00Z",
            "--execute",
        ]
    )
    assert code == 3
    assert "acknowledgement required" in capsys.readouterr().err


def test_smartapi_provider_fails_closed_when_disabled() -> None:
    from app.core.config import Settings

    with pytest.raises(Exception, match="configuration-disabled"):
        SmartApiHistoricalProvider(Settings(smartapi_enabled=False))


class FakeReadOnlyAdapter:
    def __init__(self, fail_auth: bool = False, fail_request: bool = False) -> None:
        self.fail_auth = fail_auth
        self.fail_request = fail_request
        self.authenticated = False
        self.terminations = 0
        self.requests = 0
        self.request_count = 0
        self.authentication_attempts = 0

    def authenticate(self) -> None:
        self.authentication_attempts += 1
        if self.fail_auth:
            raise RuntimeError("private authentication detail")
        self.authenticated = True

    def retrieve_historical_candles(self, _params):
        self.requests += 1
        if self.fail_request:
            raise RuntimeError("private provider detail")
        return {
            "status": True,
            "data": [["2026-08-13T09:15:00+05:30", 1, 1, 1, 1, 0]],
        }

    def terminate_session(self) -> bool:
        self.terminations += 1
        return True


def smartapi_settings():
    from app.core.config import Settings

    return Settings(
        smartapi_enabled=True,
        smartapi_api_key="placeholder",
        smartapi_client_code="placeholder",
        smartapi_pin="placeholder",
        smartapi_totp_secret="JBSWY3DPEHPK3PXP",
    )


def test_smartapi_authentication_failure_attempts_cleanup() -> None:
    adapter = FakeReadOnlyAdapter(fail_auth=True)
    provider = SmartApiHistoricalProvider(smartapi_settings(), lambda _settings: adapter)
    with pytest.raises(RuntimeError, match="private authentication detail"):
        provider.historical_candles(
            nifty_record(),
            "FIVE_MINUTE",
            datetime(2026, 8, 13, 3, 45, tzinfo=UTC),
            datetime(2026, 8, 13, 3, 50, tzinfo=UTC),
        )
    provider.close()
    assert adapter.terminations == 1


def test_smartapi_authentication_failure_is_audited(session: Session) -> None:
    instrument = Instrument(
        provider="smartapi",
        exchange="NSE",
        token="99926000",
        trading_symbol="NIFTY 50",
        underlying_symbol="NIFTY",
        instrument_type="spot",
        expiry=None,
        strike=None,
        option_type=None,
        lot_size=1,
        tick_size=Decimal("0.05"),
        active=True,
        is_synthetic=False,
    )
    session.add(instrument)
    session.commit()
    adapter = FakeReadOnlyAdapter(fail_auth=True)
    provider = SmartApiHistoricalProvider(smartapi_settings(), lambda _settings: adapter)
    with pytest.raises(HistoricalIngestionError, match="provider-or-persistence-failure"):
        ingest_history(session, provider, request(instrument), now=NOW)
    run = session.scalar(select(IngestionRun).where(IngestionRun.provider == "smartapi"))
    assert run and run.status == "failed" and run.completed_at is not None
    assert run.error_summary == "provider-or-persistence-failure"
    assert adapter.authentication_attempts == 1
    assert adapter.requests == 0
    assert adapter.terminations == 1


def test_smartapi_session_closes_after_success_and_provider_failure() -> None:
    current = nifty_record()
    success_adapter = FakeReadOnlyAdapter()
    provider = SmartApiHistoricalProvider(smartapi_settings(), lambda _settings: success_adapter)
    batch = provider.historical_candles(
        current,
        "FIVE_MINUTE",
        datetime(2026, 8, 13, 3, 45, tzinfo=UTC),
        datetime(2026, 8, 13, 3, 50, tzinfo=UTC),
    )
    assert len(batch.rows) == 1
    provider.close()
    assert success_adapter.terminations == 1

    failure_adapter = FakeReadOnlyAdapter(fail_request=True)
    provider = SmartApiHistoricalProvider(smartapi_settings(), lambda _settings: failure_adapter)
    try:
        with pytest.raises(RuntimeError, match="private provider detail"):
            provider.historical_candles(
                current,
                "FIVE_MINUTE",
                datetime(2026, 8, 13, 3, 45, tzinfo=UTC),
                datetime(2026, 8, 13, 3, 50, tzinfo=UTC),
            )
    finally:
        provider.close()
    assert failure_adapter.terminations == 1


def test_smartapi_rejects_now_expired_derivative_before_provider_request() -> None:
    adapter = FakeReadOnlyAdapter()
    provider = SmartApiHistoricalProvider(
        smartapi_settings(),
        lambda _settings: adapter,
        now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
    )
    expired_future = nifty_record(
        exchange="NFO",
        token="1",
        trading_symbol="NIFTY01JAN26FUT",
        instrument_type="future",
        expiry=datetime(2026, 1, 1).date(),
    )
    try:
        with pytest.raises(Exception, match="instrument-identity-rejected"):
            provider.historical_candles(
                expired_future,
                "FIVE_MINUTE",
                datetime(2025, 12, 1, tzinfo=UTC),
                datetime(2025, 12, 2, tzinfo=UTC),
            )
    finally:
        provider.close()
    assert adapter.requests == 0
    assert adapter.terminations == 1


def nifty_record(**changes: object) -> InstrumentRecord:
    record = InstrumentRecord(
        provider="smartapi",
        exchange="NSE",
        token="99926000",
        trading_symbol="NIFTY 50",
        underlying_symbol="NIFTY",
        instrument_type="spot",
        expiry=None,
        strike=None,
        option_type=None,
        lot_size=1,
        tick_size=Decimal("0.05"),
    )
    return replace(record, **changes)


@pytest.mark.parametrize(
    "record",
    [
        nifty_record(underlying_symbol="BANKNIFTY"),
        nifty_record(underlying_symbol="FINNIFTY"),
        nifty_record(underlying_symbol="MIDCPNIFTY"),
        nifty_record(token="wrong"),
        nifty_record(exchange="NFO"),
        nifty_record(
            exchange="NFO",
            token="1",
            trading_symbol="NIFTY27AUG2625000CE",
            instrument_type="option",
            option_type="CE",
            expiry=datetime(2026, 8, 27).date(),
            strike=None,
        ),
        nifty_record(
            exchange="NFO",
            token="1",
            trading_symbol="NIFTY01JAN26FUT",
            instrument_type="future",
            expiry=datetime(2026, 1, 1).date(),
        ),
    ],
)
def test_exact_nifty_identity_rejects_competing_or_expired_rows(
    record: InstrumentRecord,
) -> None:
    from app.smartapi.adapter import SmartApiError

    with pytest.raises(SmartApiError, match="instrument-identity-rejected"):
        validate_nifty_identity(record, NOW)


def test_exact_nifty_identity_accepts_spot_and_current_derivatives() -> None:
    validate_nifty_identity(nifty_record(), NOW)
    future = nifty_record(
        exchange="NFO",
        token="1",
        trading_symbol="NIFTY27AUG26FUT",
        instrument_type="future",
        expiry=datetime(2026, 8, 27).date(),
    )
    validate_nifty_identity(future, NOW)
    validate_nifty_identity(
        replace(
            future,
            token="2",
            trading_symbol="NIFTY27AUG2625000CE",
            instrument_type="option",
            option_type="CE",
            strike=Decimal("25000"),
        ),
        NOW,
    )


def test_provider_interfaces_have_no_forbidden_operations() -> None:
    forbidden = {
        "order",
        "account",
        "profile",
        "position",
        "holding",
        "portfolio",
        "margin",
        "gtt",
        "websocket",
    }
    names = {
        name.lower()
        for cls in (FixtureHistoricalProvider, SmartApiHistoricalProvider)
        for name in vars(cls)
    }
    assert not any(any(term in name for term in forbidden) for name in names)
