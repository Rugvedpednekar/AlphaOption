import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.market_data.provider import CandleRecord, HistoricalBatch, InstrumentRecord
from app.market_data.validation import decimal_value
from app.smartapi.adapter import ReadOnlySmartApiAdapter, SmartApiError

NIFTY_SPOT_TOKEN = "99926000"
NIFTY_DERIVATIVE_SYMBOL = re.compile(r"^NIFTY\d")


def validate_nifty_identity(instrument: InstrumentRecord, as_of: datetime) -> None:
    symbol = "".join(instrument.trading_symbol.upper().split())
    underlying = " ".join(instrument.underlying_symbol.upper().split())
    if instrument.instrument_type == "spot":
        valid = (
            instrument.exchange == "NSE"
            and instrument.token == NIFTY_SPOT_TOKEN
            and underlying == "NIFTY"
            and symbol in {"NIFTY", "NIFTY50"}
        )
    else:
        valid = (
            instrument.exchange == "NFO"
            and instrument.token.isdigit()
            and underlying == "NIFTY"
            and bool(NIFTY_DERIVATIVE_SYMBOL.match(symbol))
            and instrument.expiry is not None
            and instrument.expiry >= as_of.date()
            and (
                (instrument.instrument_type == "future" and symbol.endswith("FUT"))
                or (
                    instrument.instrument_type == "option"
                    and instrument.option_type in {"CE", "PE"}
                    and instrument.strike is not None
                    and instrument.strike >= 0
                    and symbol.endswith(instrument.option_type)
                )
            )
        )
    if not valid:
        raise SmartApiError("instrument-identity-rejected")


class FixtureHistoricalProvider:
    name = "fixture"
    is_synthetic = True

    def historical_candles(
        self, instrument: InstrumentRecord, interval: str, start: datetime, end: datetime
    ) -> HistoricalBatch:
        step = timedelta(minutes=1 if interval == "ONE_MINUTE" else 5)
        rows: list[CandleRecord] = []
        cursor = start
        sequence = 0
        while cursor < end:
            base = Decimal("100") + Decimal(sequence) / Decimal("10")
            rows.append(
                CandleRecord(
                    instrument.provider,
                    instrument.exchange,
                    instrument.token,
                    "1m" if interval == "ONE_MINUTE" else "5m",
                    cursor,
                    base,
                    base + 1,
                    base - 1,
                    base + Decimal("0.5"),
                    100 + sequence,
                    None,
                    "synthetic_fixture_history",
                    True,
                )
            )
            cursor += step
            sequence += 1
        return HistoricalBatch(tuple(rows))

    def close(self) -> None:
        return None


class SmartApiHistoricalProvider:
    """Read-only, per-instance adapter. Automated tests must inject an SDK factory."""

    name = "smartapi"
    is_synthetic = False

    def __init__(
        self,
        settings: Settings,
        adapter_factory: Callable[[Settings], ReadOnlySmartApiAdapter] = ReadOnlySmartApiAdapter,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if (
            not settings.smartapi_enabled
            or settings.trading_mode != "paper"
            or settings.enable_live_orders
        ):
            raise SmartApiError("configuration-disabled")
        self._adapter = adapter_factory(settings)
        self._now = now
        try:
            self._adapter.authenticate()
        except Exception:
            self._adapter.terminate_session()
            raise

    def historical_candles(
        self, instrument: InstrumentRecord, interval: str, start: datetime, end: datetime
    ) -> HistoricalBatch:
        # Historical ranges must not make an expired derivative look current.
        validate_nifty_identity(instrument, self._now())
        step = timedelta(minutes=1 if interval == "ONE_MINUTE" else 5)
        response = self._adapter.retrieve_historical_candles(
            {
                "exchange": instrument.exchange,
                "symboltoken": instrument.token,
                "interval": interval,
                "fromdate": start.strftime("%Y-%m-%d %H:%M"),
                # SmartAPI's end is inclusive; internal chunks are half-open.
                "todate": (end - step).strftime("%Y-%m-%d %H:%M"),
            }
        )
        data = response.get("data")
        if not response.get("status") or not isinstance(data, list):
            raise SmartApiError("provider-invalid-response")
        rows: list[CandleRecord] = []
        for raw in data:
            if not isinstance(raw, list) or len(raw) < 6:
                raise SmartApiError("provider-invalid-response")
            rows.append(
                CandleRecord(
                    instrument.provider,
                    instrument.exchange,
                    instrument.token,
                    "1m" if interval == "ONE_MINUTE" else "5m",
                    _provider_timestamp(str(raw[0])),
                    decimal_value(raw[1], "open"),
                    decimal_value(raw[2], "high"),
                    decimal_value(raw[3], "low"),
                    decimal_value(raw[4], "close"),
                    int(raw[5]),
                    int(raw[6]) if len(raw) > 6 and raw[6] is not None else None,
                    "smartapi_history",
                    False,
                )
            )
        return HistoricalBatch(tuple(rows))

    def close(self) -> None:
        self._adapter.terminate_session()


def _provider_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SmartApiError("provider-invalid-response") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    return parsed
