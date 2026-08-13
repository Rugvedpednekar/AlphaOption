import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.smartapi.adapter import ReadOnlySmartApiAdapter, SmartApiError
from app.smartapi.cli import main
from app.smartapi.probe import run_probe, select_instruments, summarize_candles
from app.smartapi.reporting import write_redacted_evidence

FAKE_VALUES = {
    "api_key": "fake-api-key-value",
    "client_code": "fake-client-code-value",
    "pin": "fake-pin-value",
    "totp_secret": "JBSWY3DPEHPK3PXP",
    "jwt": "fake-jwt-token-value",
    "refresh": "fake-refresh-token-value",
    "feed": "fake-feed-token-value",
}


def settings(**overrides):
    values = {
        "smartapi_enabled": True,
        "smartapi_api_key": SecretStr(FAKE_VALUES["api_key"]),
        "smartapi_client_code": SecretStr(FAKE_VALUES["client_code"]),
        "smartapi_pin": SecretStr(FAKE_VALUES["pin"]),
        "smartapi_totp_secret": SecretStr(FAKE_VALUES["totp_secret"]),
        "enable_live_orders": False,
        "trading_mode": "paper",
    }
    values.update(overrides)
    return Settings(**values)


class FakeSdk:
    def __init__(self, fail_candles: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_candles = fail_candles

    def generateSession(self, client_code, pin, totp):
        self.calls.append("authenticate")
        return {
            "status": True,
            "data": {
                "jwtToken": FAKE_VALUES["jwt"],
                "refreshToken": FAKE_VALUES["refresh"],
                "feedToken": FAKE_VALUES["feed"],
            },
        }

    def terminateSession(self, client_code):
        self.calls.append("terminate")
        return {"status": True}

    def getCandleData(self, params):
        self.calls.append("candles")
        if self.fail_candles:
            raise RuntimeError(f"bad {FAKE_VALUES['jwt']}")
        return {
            "status": True,
            "data": [["2026-08-13T09:15:00+05:30", 1, 2, 0.5, 1.5, 100]],
        }

    def getOIData(self, params):
        self.calls.append("oi")
        return {"status": True, "data": [{"time": "2026-08-13T09:15:00+05:30", "oi": 1}]}

    def getMarketData(self, mode, exchange_tokens):
        self.calls.append("snapshot")
        return {
            "status": True,
            "data": {"fetched": [{"exchange": "NSE", "depth": {"buy": [], "sell": []}}]},
        }


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return instrument_rows()


def instrument_rows():
    return [
        {
            "token": "1",
            "symbol": "NIFTY 50",
            "name": "NIFTY",
            "instrumenttype": "AMXIDX",
            "exch_seg": "NSE",
            "expiry": "",
            "strike": "-1.000000",
        },
        {
            "token": "2",
            "symbol": "NIFTY27AUG26FUT",
            "name": "NIFTY",
            "instrumenttype": "FUTIDX",
            "exch_seg": "NFO",
            "expiry": "27AUG2026",
            "strike": "-1.000000",
        },
        {
            "token": "3",
            "symbol": "NIFTY27AUG2624000CE",
            "name": "NIFTY",
            "instrumenttype": "OPTIDX",
            "exch_seg": "NFO",
            "expiry": "27AUG2026",
            "strike": "2400000",
        },
        {
            "token": "4",
            "symbol": "NIFTY27AUG2624000PE",
            "name": "NIFTY",
            "instrumenttype": "OPTIDX",
            "exch_seg": "NFO",
            "expiry": "27AUG2026",
            "strike": "2400000",
        },
    ]


def make_adapter(fake: FakeSdk, config=None):
    return ReadOnlySmartApiAdapter(
        config or settings(),
        sdk_factory=lambda _: fake,
        instrument_get=lambda *args, **kwargs: FakeResponse(),
        sleep=lambda _: None,
    )


def test_missing_configuration_fails_closed():
    adapter = ReadOnlySmartApiAdapter(settings(smartapi_api_key=None), sleep=lambda _: None)
    with pytest.raises(SmartApiError, match="configuration-missing"):
        adapter.authenticate()


def test_disabled_and_acknowledgement_gates_make_zero_calls(monkeypatch, capsys):
    monkeypatch.setenv("SMARTAPI_ENABLED", "false")
    assert main(["probe", "--execute", "--acknowledge-read-only"]) == 2
    assert "smartapi-disabled" in capsys.readouterr().out
    monkeypatch.setenv("SMARTAPI_ENABLED", "true")
    assert main(["probe", "--execute"]) == 2
    assert "read-only-acknowledgement-required" in capsys.readouterr().out


def test_dry_run_has_zero_network_calls(monkeypatch, capsys):
    monkeypatch.setenv("SMARTAPI_ENABLED", "false")
    assert main(["probe", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "NETWORK_CALLS=0" in output
    assert "READ_ONLY_ACKNOWLEDGED=false" in output


def test_authentication_attempts_are_bounded():
    fake = FakeSdk()
    adapter = make_adapter(fake)
    adapter.authenticate()
    adapter.authenticate()
    with pytest.raises(SmartApiError, match="authentication-attempt-limit"):
        adapter.authenticate()
    assert fake.calls.count("authenticate") == 2


def test_selection_is_deterministic():
    first = select_instruments(instrument_rows(), datetime(2026, 8, 13, tzinfo=UTC).date())
    second = select_instruments(
        list(reversed(instrument_rows())), datetime(2026, 8, 13, tzinfo=UTC).date()
    )
    assert first == second
    assert [item.role for item in first] == [
        "nifty-spot",
        "nearest-active-future",
        "representative-active-ce",
        "representative-active-pe",
    ]


def test_candle_summary_contains_no_prices():
    result = summarize_candles(
        "test", {"status": True, "data": [["time", 101, 102, 99, 100, 5]]}, "from", "to"
    )
    serialized = json.dumps(result.details)
    assert result.details["ohlc_present"] is True
    assert "101" not in serialized
    assert "102" not in serialized


@pytest.mark.parametrize("fail", [False, True])
def test_session_termination_occurs_on_success_and_failure(fail):
    fake = FakeSdk(fail_candles=fail)
    report = run_probe(make_adapter(fake), datetime(2026, 8, 13, tzinfo=UTC))
    assert fake.calls[-1] == "terminate"
    assert report.session_terminated is True
    assert report.orders_sent is False


def test_calls_are_sequential_and_bounded():
    fake = FakeSdk()
    report = run_probe(make_adapter(fake), datetime(2026, 8, 13, tzinfo=UTC))
    assert report.provider_request_count == 14
    assert fake.calls == [
        "authenticate",
        "candles",
        "candles",
        "candles",
        "candles",
        "oi",
        "candles",
        "oi",
        "candles",
        "oi",
        "snapshot",
        "terminate",
    ]


def test_errors_cli_and_evidence_do_not_leak_secrets(tmp_path: Path, capsys):
    fake = FakeSdk(fail_candles=True)
    report = run_probe(make_adapter(fake), datetime(2026, 8, 13, tzinfo=UTC))
    path = write_redacted_evidence(report, tmp_path)
    combined = path.read_text(encoding="utf-8") + capsys.readouterr().out
    for value in FAKE_VALUES.values():
        assert value not in combined


def test_adapter_exposes_no_order_related_method():
    public = {name.lower() for name in dir(ReadOnlySmartApiAdapter) if not name.startswith("_")}
    forbidden = {"placeorder", "modifyorder", "cancelorder", "orderbook", "tradebook", "gtt"}
    assert public.isdisjoint(forbidden)
