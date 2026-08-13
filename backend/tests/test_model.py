from app.models import IngestionRun, Instrument, MarketCandle, SystemEvent


def test_system_event_table_shape() -> None:
    columns = set(SystemEvent.__table__.columns.keys())
    assert columns == {"id", "event_type", "severity", "message", "created_at"}


def test_market_data_tables_are_registered() -> None:
    assert Instrument.__tablename__ == "instruments"
    assert MarketCandle.__tablename__ == "market_candles"
    assert IngestionRun.__tablename__ == "ingestion_runs"
