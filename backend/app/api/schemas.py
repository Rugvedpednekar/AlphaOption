from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    status: Literal["healthy", "unhealthy"]


class SystemStatus(BaseModel):
    service_status: Literal["healthy", "degraded"]
    application_version: str
    operating_mode: Literal["backtest", "replay", "paper"]
    live_orders_enabled: Literal[False]
    database: DatabaseHealth
    timestamp_utc: datetime
    market_timezone: Literal["Asia/Kolkata"]
