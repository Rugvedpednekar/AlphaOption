from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import DatabaseHealth, SystemStatus
from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["system"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseDependency = Annotated[Session, Depends(get_db)]


def database_status(db: Session) -> DatabaseHealth:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return DatabaseHealth(status="unhealthy")
    return DatabaseHealth(status="healthy")


def build_status(settings: Settings, db_health: DatabaseHealth) -> SystemStatus:
    return SystemStatus(
        service_status="healthy" if db_health.status == "healthy" else "degraded",
        application_version=settings.app_version,
        operating_mode=settings.trading_mode,
        live_orders_enabled=False,
        database=db_health,
        timestamp_utc=datetime.now(UTC),
        market_timezone="Asia/Kolkata",
    )


@router.get("/health", response_model=SystemStatus)
def health(settings: SettingsDependency, db: DatabaseDependency) -> SystemStatus:
    return build_status(settings, database_status(db))


@router.get("/system/status", response_model=SystemStatus)
def system_status(settings: SettingsDependency, db: DatabaseDependency) -> SystemStatus:
    return build_status(settings, database_status(db))
