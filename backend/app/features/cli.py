import argparse
import sys
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.features.engine import FeatureEngineeringError, FeatureRequest, build, preview


def _timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be ISO-8601") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="AlphaOption leakage-safe feature utilities")
    commands = result.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("--instrument-id", type=uuid.UUID, required=True)
    build_parser.add_argument("--interval", choices=("FIVE_MINUTE",), required=True)
    build_parser.add_argument("--from", dest="start", type=_timestamp, required=True)
    build_parser.add_argument("--to", dest="end", type=_timestamp, required=True)
    build_parser.add_argument("--feature-version", required=True)
    action = build_parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--execute", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    request = FeatureRequest(
        args.instrument_id, args.interval, args.start, args.end, args.feature_version
    )
    try:
        with SessionLocal() as session:
            if args.dry_run:
                result = preview(session, request)
                print(
                    f"eligible={result['eligible_candles']} warmup={result['warmup_bars']} "
                    f"target_tail_15m={result['expected_target_tail_15m']} "
                    f"target_tail_30m={result['expected_target_tail_30m']} "
                    f"source={result['source_classification']}"
                )
                print("dry-run: zero database writes and zero provider calls")
                return 0
            run = build(session, request)
    except FeatureEngineeringError as exc:
        print(f"feature build failed: {exc.category}", file=sys.stderr)
        return 2
    except Exception:
        print("feature build failed: database-connection-failure", file=sys.stderr)
        return 3
    print(
        f"status={run.status} received={run.records_received} created={run.records_created} "
        f"skipped={run.records_skipped} rejected={run.records_rejected} "
        f"source={run.source_classification}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
