import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging_config import get_logger
from app.core.background_jobs import daily_expiry_job, run_startup_expiry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting")
    run_startup_expiry()
    expiry_task = asyncio.create_task(daily_expiry_job())
    yield
    expiry_task.cancel()
    logger.info("Application shutting down")
