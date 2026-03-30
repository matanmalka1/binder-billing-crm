import asyncio
from typing import TYPE_CHECKING

from app.core import get_logger
from app.database import SessionLocal
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.admin_actions import expire_overdue_requests

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Exported so config.py can override in tests or deployment without touching this file.
# Default: run once per day (86 400 seconds).
try:
    from app.config import config as _cfg
    _INTERVAL: int = getattr(_cfg, "BACKGROUND_JOB_INTERVAL_SECONDS", 86_400)
except Exception:  # guard against import-time failures in tests
    _INTERVAL = 86_400

# Maximum reminders to dispatch per job run.
# Keeps the DB session short-lived even when many reminders accumulate.
_REMINDER_BATCH_SIZE = 200


def run_startup_expiry() -> None:
    """Run signature expiry check once at application startup."""
    db = SessionLocal()
    try:
        count = expire_overdue_requests(SignatureRequestRepository(db))
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
            count = expire_overdue_requests(SignatureRequestRepository(db))
            if count:
                logger.info("Daily job: expired %d overdue signature request(s)", count)
        except Exception:
            logger.exception("Daily expiry job failed")
        finally:
            db.close()


async def daily_reminder_job() -> None:
    """Dispatch pending reminders once per day in the background.

    For each due reminder the job:
    1. Sends an actual notification via NotificationService.
    2. Only marks the reminder as SENT after a successful send.

    Reminders are processed in batches of _REMINDER_BATCH_SIZE to keep
    the DB session short-lived.
    """
    while True:
        await asyncio.sleep(_INTERVAL)
        db = SessionLocal()
        try:
            # Import here to avoid circular imports at module load time.
            from app.reminders.services.reminder_service import ReminderService
            from app.notification.services.notification_service import NotificationService

            reminder_svc = ReminderService(db)
            notification_svc = NotificationService(db)

            items, _total, _names = reminder_svc.get_pending_reminders(
                page=1, page_size=_REMINDER_BATCH_SIZE
            )

            sent = failed = 0
            for reminder in items:
                try:
                    # Claim before sending — prevents double-send if process restarts
                    # between send and mark_sent. Stuck PROCESSING rows are observable.
                    claimed = reminder_svc.claim_for_processing(reminder.id)
                    if not claimed:
                        continue
                    notification_svc.notify_payment_reminder(
                        business_id=reminder.business_id,
                        reminder_text=reminder.message,
                    )
                    reminder_svc.mark_sent(reminder.id)
                    sent += 1
                    logger.info(
                        "Reminder dispatched id=%d type=%s business_id=%d",
                        reminder.id,
                        reminder.reminder_type,
                        reminder.business_id,
                    )
                except Exception:
                    failed += 1
                    logger.exception(
                        "Failed to dispatch reminder id=%d type=%s",
                        reminder.id,
                        reminder.reminder_type,
                    )

            if sent or failed:
                logger.info(
                    "Daily reminder job finished: sent=%d failed=%d", sent, failed
                )
        except Exception:
            logger.exception("Daily reminder job failed")
        finally:
            db.close()
