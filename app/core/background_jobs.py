import asyncio

import sys

from app.core import get_logger
from app.database import SessionLocal
from app.reminders.services.reminder_service import ReminderService
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.admin_actions import expire_overdue_requests

_INTERVAL = 86_400
logger = get_logger(__name__)


def _expire(repo):
    return sys.modules[__name__].expire_overdue_requests(repo)


def run_startup_expiry() -> None:
    """Run signature expiry check once at application startup."""
    db = SessionLocal()
    try:
        count = _expire(SignatureRequestRepository(db))
        if count:
            logger.info("Expired %d overdue signature request(s) on startup", count)
    finally:
        db.close()


async def daily_expiry_job() -> None:
    """Run signature expiry check once per day in the background."""
    while True:
        await asyncio.sleep(_INTERVAL)
        db = SessionLocal()
        try:
            count = _expire(SignatureRequestRepository(db))
            if count:
                logger.info("Daily job: expired %d overdue signature request(s)", count)
        except Exception:
            logger.exception("Daily expiry job failed")
        finally:
            db.close()


async def daily_reminder_job() -> None:
    """Dispatch pending reminders once per day in the background."""
    while True:
        await asyncio.sleep(_INTERVAL)
        db = SessionLocal()
        try:
            svc = ReminderService(db)
            items, _total, _names = svc.get_pending_reminders()
            for reminder in items:
                logger.info("Dispatching reminder id=%d type=%s", reminder.id, reminder.reminder_type)
                svc.mark_sent(reminder.id)
        except Exception:
            logger.exception("Daily reminder job failed")
        finally:
            db.close()
