from fastapi.testclient import TestClient


def assert_safe_status(payload: dict[str, object]) -> None:
    assert payload["service_status"] == "healthy"
    assert payload["application_version"] == "0.1.0"
    assert payload["operating_mode"] == "paper"
    assert payload["live_orders_enabled"] is False
    assert payload["database"] == {"status": "healthy"}
    assert payload["market_timezone"] == "Asia/Kolkata"
    assert "timestamp_utc" in payload


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert_safe_status(response.json())


def test_system_status(client: TestClient) -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    assert_safe_status(response.json())
