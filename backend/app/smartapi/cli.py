import argparse
from pathlib import Path

from pydantic import ValidationError

from app.core.config import Settings
from app.smartapi.adapter import ReadOnlySmartApiAdapter
from app.smartapi.probe import run_probe
from app.smartapi.reporting import write_redacted_evidence


def _readiness(settings: Settings) -> dict[str, bool]:
    names = (
        "smartapi_api_key",
        "smartapi_client_code",
        "smartapi_pin",
        "smartapi_totp_secret",
    )
    return {
        name.upper(): bool(
            getattr(settings, name) and getattr(settings, name).get_secret_value().strip()
        )
        for name in names
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AlphaOption read-only SmartAPI capability probe")
    parser.add_argument("command", choices=["probe"])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-read-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        settings = Settings()
    except ValidationError:
        print("configuration_valid=false")
        return 2
    readiness = _readiness(settings)
    if args.dry_run:
        print(f"SMARTAPI_ENABLED={str(settings.smartapi_enabled).lower()}")
        print(f"LIVE_ORDERS_DISABLED={str(not settings.enable_live_orders).lower()}")
        print("READ_ONLY_ACKNOWLEDGED=false")
        for name, ready in readiness.items():
            print(f"{name}_PRESENT={str(ready).lower()}")
        print("NETWORK_CALLS=0")
        return 0
    if not settings.smartapi_enabled:
        print("probe_status=configuration-error")
        print("reason=smartapi-disabled")
        return 2
    if settings.enable_live_orders:
        print("probe_status=configuration-error")
        print("reason=live-orders-not-disabled")
        return 2
    if not args.acknowledge_read_only:
        print("probe_status=configuration-error")
        print("reason=read-only-acknowledgement-required")
        return 2
    if not all(readiness.values()):
        print("probe_status=configuration-error")
        print("reason=required-configuration-missing")
        return 2
    report = run_probe(ReadOnlySmartApiAdapter(settings))
    evidence = write_redacted_evidence(
        report, Path(__file__).resolve().parents[3] / "artifacts" / "smartapi-probes"
    )
    print(f"probe_status={report.authentication.status}")
    print(f"provider_requests={report.provider_request_count}")
    print(f"session_terminated={str(report.session_terminated).lower()}")
    print(f"evidence_file={evidence.name}")
    print("orders_sent=false")
    failed = report.authentication.status != "verified" or any(
        result.status in {"provider-error", "credential/configuration-error"}
        for result in report.capabilities
    )
    return 3 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
