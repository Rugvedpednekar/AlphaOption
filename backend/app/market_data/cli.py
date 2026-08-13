import argparse

from app.db.session import SessionLocal
from app.market_data.fixture_provider import FixtureProvider
from app.market_data.ingestion import ingest_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaOption market-data utilities")
    parser.add_argument("command", choices=["load-fixture"])
    args = parser.parse_args()
    if args.command == "load-fixture":
        with SessionLocal() as session:
            run = ingest_provider(session, FixtureProvider())
        print(f"SYNTHETIC fixture: status={run.status}")
        print(
            f"received={run.records_received} inserted={run.records_inserted} "
            f"updated={run.records_updated} rejected={run.records_rejected}"
        )


if __name__ == "__main__":
    main()
