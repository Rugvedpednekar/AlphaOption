import argparse
import sys
import uuid
from datetime import datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.market_data.fixture_provider import FixtureProvider
from app.market_data.historical import (
    HistoricalIngestionError,
    HistoricalRequest,
    build_chunks,
    ingest_history,
    normalize_request,
)
from app.market_data.historical_providers import (
    FixtureHistoricalProvider,
    SmartApiHistoricalProvider,
)
from app.market_data.ingestion import ingest_provider


def timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be ISO-8601") from exc
    return parsed


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="AlphaOption market-data utilities")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("load-fixture")
    history = commands.add_parser("ingest-history")
    history.add_argument("--provider", choices=("fixture", "smartapi"), required=True)
    history.add_argument("--instrument-id", type=uuid.UUID, required=True)
    history.add_argument("--interval", choices=("ONE_MINUTE", "FIVE_MINUTE"), required=True)
    history.add_argument("--from", dest="start", type=timestamp, required=True)
    history.add_argument("--to", dest="end", type=timestamp, required=True)
    action = history.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--execute", action="store_true")
    history.add_argument("--acknowledge-read-only", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "load-fixture":
        with SessionLocal() as session:
            run = ingest_provider(session, FixtureProvider())
        print(f"SYNTHETIC fixture: status={run.status}")
        return 0
    request = HistoricalRequest(args.instrument_id, args.interval, args.start, args.end)
    try:
        request = normalize_request(request)
        chunks = build_chunks(request)
    except HistoricalIngestionError as exc:
        print(f"validation failure: {exc.category}", file=sys.stderr)
        return 2
    print(f"provider={args.provider} interval={args.interval} chunks={len(chunks)}")
    for index, chunk in enumerate(chunks, 1):
        print(f"chunk {index}: {chunk.start.isoformat()} to {chunk.end.isoformat()}")
    if args.dry_run:
        print("dry-run: zero provider calls and zero database writes")
        return 0
    if args.provider == "smartapi" and not args.acknowledge_read_only:
        print("configuration failure: read-only acknowledgement required", file=sys.stderr)
        return 3
    try:
        provider = (
            FixtureHistoricalProvider()
            if args.provider == "fixture"
            else SmartApiHistoricalProvider(get_settings())
        )
        with SessionLocal() as session:
            run = ingest_history(
                session,
                provider,
                request,
                throttle_seconds=1.1 if args.provider == "smartapi" else 0,
            )
    except Exception as exc:
        category = (
            exc.category
            if isinstance(exc, HistoricalIngestionError)
            else "configuration-or-persistence-failure"
        )
        print(f"execution failure: {category}", file=sys.stderr)
        return 4
    print(
        f"status={run.status} received={run.records_received} "
        f"inserted={run.records_inserted} duplicates={run.records_duplicates} "
        f"rejected={run.records_rejected}"
    )
    if isinstance(provider, SmartApiHistoricalProvider):
        print(f"authentication_attempts={provider.authentication_attempts}")
        print(f"provider_requests={provider.request_count}")
        print(f"session_terminated={str(provider.session_terminated is True).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
