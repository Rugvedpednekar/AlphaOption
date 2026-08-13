import json
from datetime import date
from decimal import Decimal
from importlib.resources import files

from app.market_data.provider import CandleRecord, InstrumentRecord
from app.market_data.validation import decimal_value, parse_timestamp


class FixtureProvider:
    name = "fixture"
    dataset = "synthetic_nifty_phase2a"
    is_synthetic = True

    def __init__(self) -> None:
        path = files("app.market_data.fixtures").joinpath("synthetic_nifty.json")
        self.payload = json.loads(path.read_text(encoding="utf-8"))

    def instruments(self) -> list[InstrumentRecord]:
        return [
            InstrumentRecord(
                provider=self.name,
                exchange=item["exchange"],
                token=item["token"],
                trading_symbol=item["trading_symbol"],
                underlying_symbol="NIFTY",
                instrument_type=item["instrument_type"],
                expiry=date.fromisoformat(item["expiry"]) if item.get("expiry") else None,
                strike=Decimal(str(item["strike"])) if item.get("strike") is not None else None,
                option_type=item.get("option_type"),
                lot_size=item["lot_size"],
                tick_size=Decimal(str(item["tick_size"])),
                is_synthetic=True,
            )
            for item in self.payload["instruments"]
        ]

    def candles(self) -> list[CandleRecord]:
        return [
            CandleRecord(
                provider=self.name,
                exchange=item["exchange"],
                token=item["token"],
                timeframe=item["timeframe"],
                candle_timestamp=parse_timestamp(item["timestamp"]),
                open=decimal_value(item["open"], "open"),
                high=decimal_value(item["high"], "high"),
                low=decimal_value(item["low"], "low"),
                close=decimal_value(item["close"], "close"),
                volume=item["volume"],
                open_interest=item.get("open_interest"),
                source="synthetic_fixture",
                is_synthetic=True,
            )
            for item in self.payload["candles"]
        ]
