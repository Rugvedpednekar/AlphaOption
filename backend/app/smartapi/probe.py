from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.smartapi.adapter import ReadOnlySmartApiAdapter, SmartApiError
from app.smartapi.redaction import safe_provider_code
from app.smartapi.types import CapabilityResult, ProbeInstrument, ProbeReport

INTERVALS = ("ONE_MINUTE", "FIVE_MINUTE")


def _parse_expiry(value: object) -> date | None:
    text = str(value or "").strip()
    for pattern in ("%d%b%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def select_instruments(rows: list[dict[str, Any]], today: date) -> tuple[ProbeInstrument, ...]:
    candidates: list[ProbeInstrument] = []
    for row in rows:
        exchange = str(row.get("exch_seg", "")).upper()
        symbol = str(row.get("symbol", ""))
        name = str(row.get("name", ""))
        kind = str(row.get("instrumenttype", "")).upper()
        if "NIFTY" not in f"{name} {symbol}".upper() or "BANKNIFTY" in symbol.upper():
            continue
        expiry = _parse_expiry(row.get("expiry"))
        token = str(row.get("token", ""))
        if not token:
            continue
        role = ""
        if exchange == "NSE" and (kind in {"AMXIDX", "INDEX"} or token == "99926000"):
            role = "nifty-spot"
        elif exchange == "NFO" and expiry and expiry >= today and kind == "FUTIDX":
            role = "nearest-active-future"
        elif exchange == "NFO" and expiry and expiry >= today and kind == "OPTIDX":
            if symbol.upper().endswith("CE"):
                role = "representative-active-ce"
            elif symbol.upper().endswith("PE"):
                role = "representative-active-pe"
        if role:
            raw_strike = row.get("strike")
            try:
                strike = (
                    float(raw_strike) / 100 if raw_strike not in (None, "", "-1.000000") else None
                )
            except (TypeError, ValueError):
                strike = None
            candidates.append(ProbeInstrument(role, exchange, token, symbol, expiry, strike, kind))

    def order(item: ProbeInstrument) -> tuple[Any, ...]:
        role_order = {
            "nifty-spot": 0,
            "nearest-active-future": 1,
            "representative-active-ce": 2,
            "representative-active-pe": 3,
        }
        return (role_order[item.role], item.expiry or date.max, item.strike or 0, item.symbol)

    selected: list[ProbeInstrument] = []
    for role in (
        "nifty-spot",
        "nearest-active-future",
        "representative-active-ce",
        "representative-active-pe",
    ):
        role_items = sorted((item for item in candidates if item.role == role), key=order)
        if not role_items:
            continue
        if role.startswith("representative"):
            future = next((item for item in selected if item.role == "nearest-active-future"), None)
            same_expiry = [item for item in role_items if future and item.expiry == future.expiry]
            selected.append((same_expiry or role_items)[len(same_expiry or role_items) // 2])
        else:
            selected.append(role_items[0])
    return tuple(selected)


def _response_result(capability: str, response: dict[str, Any], details: dict[str, Any]):
    if response.get("status") is True:
        return CapabilityResult(capability, "verified", details)
    return CapabilityResult(
        capability,
        "provider-error",
        details,
        safe_provider_code(response.get("errorcode")),
    )


def summarize_candles(
    capability: str, response: dict[str, Any], requested_from: str, requested_to: str
) -> CapabilityResult:
    rows = response.get("data") if isinstance(response, dict) else None
    rows = rows if isinstance(rows, list) else []
    timestamps = [str(row[0]) for row in rows if isinstance(row, list) and row]
    field_counts = [len(row) for row in rows if isinstance(row, list)]
    details = {
        "requested_from": requested_from,
        "requested_to": requested_to,
        "row_count": len(rows),
        "earliest_timestamp": min(timestamps) if timestamps else None,
        "latest_timestamp": max(timestamps) if timestamps else None,
        "field_count": max(field_counts, default=0),
        "ohlc_present": any(count >= 5 for count in field_counts),
        "volume_present": any(count >= 6 for count in field_counts),
    }
    result = _response_result(capability, response, details)
    if result.status == "verified" and not rows:
        return CapabilityResult(capability, "not-testable", details)
    return result


def summarize_oi(capability: str, response: dict[str, Any]) -> CapabilityResult:
    rows = response.get("data") if isinstance(response, dict) else None
    rows = rows if isinstance(rows, list) else []
    values = [row.get("oi") for row in rows if isinstance(row, dict) and "oi" in row]
    details = {
        "row_count": len(rows),
        "oi_field_present": bool(values),
        "oi_nullable": any(value is None for value in values),
    }
    result = _response_result(capability, response, details)
    if result.status == "verified" and not rows:
        return CapabilityResult(capability, "not-testable", details)
    return result


def summarize_snapshot(response: dict[str, Any]) -> CapabilityResult:
    fetched = (response.get("data") or {}).get("fetched") if isinstance(response, dict) else None
    rows = fetched if isinstance(fetched, list) else []
    keys = sorted({str(key) for row in rows if isinstance(row, dict) for key in row})
    depth = any(isinstance(row, dict) and bool(row.get("depth")) for row in rows)
    details = {
        "instrument_count": len(rows),
        "field_names": keys,
        "depth_present": depth,
        "historical_bid_ask_available": False,
    }
    result = _response_result("current-full-snapshot", response, details)
    if result.status == "verified" and not rows:
        return CapabilityResult("current-full-snapshot", "not-testable", details)
    return result


def run_probe(adapter: ReadOnlySmartApiAdapter, now: datetime | None = None) -> ProbeReport:
    started = (now or datetime.now(UTC)).astimezone(UTC)
    capabilities: list[CapabilityResult] = []
    instruments: tuple[ProbeInstrument, ...] = ()
    session_terminated: bool | None = None
    auth = CapabilityResult("authentication", "credential/configuration-error")
    try:
        adapter.authenticate()
        auth = CapabilityResult("authentication", "verified", {"session_created": True})
        master = adapter.retrieve_instrument_master()
        instruments = select_instruments(master, started.date())
        found_roles = {item.role for item in instruments}
        capabilities.append(
            CapabilityResult(
                "instrument-discovery",
                "verified" if len(found_roles) == 4 else "not-testable",
                {
                    "roles_found": sorted(found_roles),
                    "expired_contract_identifiers": "not-testable",
                },
            )
        )
        recent_from = (started - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        recent_to = started.strftime("%Y-%m-%d %H:%M")
        older_from = (started - timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        for item in instruments:
            intervals = INTERVALS if item.role == "nifty-spot" else ("FIVE_MINUTE",)
            for interval in intervals:
                response = adapter.retrieve_historical_candles(
                    {
                        "exchange": item.exchange,
                        "symboltoken": item.token,
                        "interval": interval,
                        "fromdate": recent_from,
                        "todate": recent_to,
                    }
                )
                capabilities.append(
                    summarize_candles(
                        f"candles:{item.role}:{interval}", response, recent_from, recent_to
                    )
                )
            if item.role == "nifty-spot":
                response = adapter.retrieve_historical_candles(
                    {
                        "exchange": item.exchange,
                        "symboltoken": item.token,
                        "interval": "FIVE_MINUTE",
                        "fromdate": older_from,
                        "todate": recent_from,
                    }
                )
                capabilities.append(
                    summarize_candles(
                        "candles:nifty-spot:older-lookback", response, older_from, recent_from
                    )
                )
            elif item.exchange == "NFO":
                response = adapter.retrieve_historical_oi(
                    {
                        "exchange": item.exchange,
                        "symboltoken": item.token,
                        "interval": "FIVE_MINUTE",
                        "fromdate": recent_from,
                        "todate": recent_to,
                    }
                )
                capabilities.append(summarize_oi(f"historical-oi:{item.role}", response))
        snapshot_tokens: dict[str, list[str]] = {}
        for item in instruments:
            snapshot_tokens.setdefault(item.exchange, []).append(item.token)
        if snapshot_tokens:
            capabilities.append(
                summarize_snapshot(adapter.retrieve_market_snapshot(snapshot_tokens))
            )
        else:
            capabilities.append(CapabilityResult("current-full-snapshot", "not-testable"))
    except SmartApiError as exc:
        if auth.status != "verified":
            auth = CapabilityResult(
                "authentication", "credential/configuration-error", provider_code=exc.provider_code
            )
        else:
            capabilities.append(
                CapabilityResult("probe", "provider-error", provider_code=exc.provider_code)
            )
    finally:
        session_terminated = adapter.terminate_session()
    completed = datetime.now(UTC)
    try:
        from SmartApi.version import __version__ as sdk_version
    except ImportError:
        sdk_version = "not-installed"
    return ProbeReport(
        started.isoformat(),
        completed.isoformat(),
        str(sdk_version),
        adapter.request_count,
        auth,
        tuple(capabilities),
        tuple(item.role for item in instruments),
        INTERVALS,
        session_terminated,
    )
