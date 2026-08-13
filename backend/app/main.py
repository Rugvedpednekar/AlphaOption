import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.market_data import router as market_data_router
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "AlphaOption API starting",
        extra={
            "context": {
                "application_version": settings.app_version,
                "operating_mode": settings.trading_mode,
                "live_orders_enabled": False,
            }
        },
    )
    yield
    logger.info("AlphaOption API stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local paper-trading research foundation. Live order routes do not exist.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(router)
app.include_router(market_data_router)
