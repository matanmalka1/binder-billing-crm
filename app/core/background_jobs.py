import asyncio
from typing import Callable

from app.core.logging_config import get_logger
from app.database import SessionLocal
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.signature_requests.services.admin_actions import expire_overdue_requests

logger = get_logger(__name__)

try:
    from app.config import config as _cfg

    _INTERVAL: int = getattr(_cfg, "BACKGROUND_JOB_INTERVAL_SECONDS", 86_400)
except Exception:
    _INTERVAL = 86_400


def run_startup_expiry() -> None:
    db = SessionLocal()
    try:
        count = expire_overdue_requests(SignatureRequestRepository(db))
        if count:
            logger.info("Expired %d overdue signature request(s) on startup", count)
    finally:
        db.close()


async def _run_job(name: str, task: Callable) -> None:
    while True:
        await asyncio.sleep(_INTERVAL)
        db = SessionLocal()
        try:
            task(db)
        except Exception:
            logger.exception("%s failed", name)
        finally:
            db.close()


def _expiry_task(db) -> None:
    count = expire_overdue_requests(SignatureRequestRepository(db))
    if count:
        logger.info("Daily job: expired %d overdue signature request(s)", count)


async def daily_expiry_job() -> None:
    await _run_job("daily_expiry_job", _expiry_task)
