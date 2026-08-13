from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import app


class HealthyDatabase:
    def execute(self, _statement: object) -> None:
        return None


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql+psycopg://placeholder:placeholder@localhost/placeholder"
    )
    app.dependency_overrides[get_db] = lambda: HealthyDatabase()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
