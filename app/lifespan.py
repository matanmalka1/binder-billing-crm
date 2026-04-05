import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging_config import get_logger
from app.core.background_jobs import daily_expiry_job, daily_reminder_job, daily_vat_compliance_job, run_startup_expiry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with graceful startup and shutdown."""
    logger.info("Application starting")
    run_startup_expiry()
    expiry_task = asyncio.create_task(daily_expiry_job())
    reminder_task = asyncio.create_task(daily_reminder_job())
    vat_compliance_task = asyncio.create_task(daily_vat_compliance_job())
    yield
    expiry_task.cancel()
    reminder_task.cancel()
    vat_compliance_task.cancel()
    logger.info("Application shutting down")
