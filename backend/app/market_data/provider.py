from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class InstrumentRecord:
    provider: str
    exchange: str
    token: str
    trading_symbol: str
    underlying_symbol: str
    instrument_type: str
    expiry: date | None
    strike: Decimal | None
    option_type: str | None
    lot_size: int
    tick_size: Decimal
    active: bool = True
    is_synthetic: bool = False


@dataclass(frozen=True)
class CandleRecord:
    provider: str
    exchange: str
    token: str
    timeframe: str
    candle_timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_interest: int | None
    source: str
    is_synthetic: bool = False


@dataclass(frozen=True)
class HistoricalBatch:
    rows: tuple[CandleRecord, ...]
    complete: bool = True


class MarketDataProvider(Protocol):
    name: str
    dataset: str
    is_synthetic: bool

    def instruments(self) -> list[InstrumentRecord]: ...
    def candles(self) -> list[CandleRecord]: ...


class HistoricalCandleProvider(Protocol):
    name: str
    is_synthetic: bool

    def historical_candles(
        self,
        instrument: InstrumentRecord,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> HistoricalBatch: ...

    def close(self) -> None: ...
