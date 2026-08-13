from app.models.system_event import SystemEvent


def test_system_event_table_shape() -> None:
    columns = set(SystemEvent.__table__.columns.keys())
    assert columns == {"id", "event_type", "severity", "message", "created_at"}
