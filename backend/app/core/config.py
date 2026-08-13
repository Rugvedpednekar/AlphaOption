from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AlphaOption API"
    app_version: str = "0.1.0"
    app_env: str = "local"
    trading_mode: Literal["backtest", "replay", "paper"] = "paper"
    enable_live_orders: bool = False
    market_timezone: str = "Asia/Kolkata"
    database_url: str = Field(
        default="postgresql+psycopg://alphaoption:alphaoption_local@db:5432/alphaoption"
    )
    cors_origins: str = "http://localhost:3000"

    @field_validator("enable_live_orders")
    @classmethod
    def reject_live_orders(cls, enabled: bool) -> bool:
        if enabled:
            raise ValueError(
                "SAFETY ERROR: live order execution is not implemented or permitted; "
                "ENABLE_LIVE_ORDERS must be false"
            )
        return enabled

    @field_validator("market_timezone")
    @classmethod
    def require_market_timezone(cls, timezone: str) -> str:
        if timezone != "Asia/Kolkata":
            raise ValueError("MARKET_TIMEZONE must be Asia/Kolkata")
        return timezone

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
