import asyncio
from typing import TYPE_CHECKING, Callable

from app.core.messages import VAT_OVERDUE_REMINDER_MESSAGE
from app.core.logging_config import get_logger
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
REMINDER_BATCH_SIZE = 200
_SYSTEM_ACTOR_ID = 0


def run_startup_expiry() -> None:
    """Run signature expiry check once at application startup."""
    db = SessionLocal()
    try:
        count = expire_overdue_requests(SignatureRequestRepository(db))
        if count:
            logger.info("Expired %d overdue signature request(s) on startup", count)
    finally:
        db.close()


async def _run_job(name: str, task: Callable) -> None:
    """Shared background job loop: sleep → open session → run task → close session."""
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
    """Run signature expiry check once per day in the background."""
    await _run_job("daily_expiry_job", _expiry_task)


def _vat_compliance_task(db) -> None:
    from datetime import date as _date
    from app.reminders.models.reminder import ReminderType
    from app.reminders.repositories.reminder_repository import ReminderRepository
    from app.tax_deadline.models.tax_deadline import DeadlineType
    from app.tax_deadline.repositories.tax_deadline_query_repository import TaxDeadlineQueryRepository
    from app.vat_reports.repositories.vat_compliance_repository import VatComplianceRepository

    today = _date.today()
    overdue = VatComplianceRepository(db).get_overdue_unfiled(today)
    reminder_repo = ReminderRepository(db)
    deadline_repo = TaxDeadlineQueryRepository(db)
    created = 0
    for row in overdue:
        # Resolve the existing TaxDeadline record for this client+period.
        # due_date on that record is the authoritative deadline (19th for online filers).
        # Using tax_deadline_id as the idempotency key prevents duplicate reminders.
        existing = deadline_repo.list_by_client_record(
            row.client_record_id,
            deadline_type=DeadlineType.VAT,
            period=row.period,
        )
        if not existing:
            logger.warning(
                "VAT compliance: no TaxDeadline found for client_record_id=%d period=%s — skipping",
                row.client_record_id,
                row.period,
            )
            continue
        tax_deadline = existing[0]
        if reminder_repo.exists_vat_compliance_reminder(row.client_record_id, tax_deadline.id):
            continue
        reminder_repo.create(
            client_record_id=row.client_record_id,
            reminder_type=ReminderType.VAT_FILING,
            target_date=tax_deadline.due_date,
            days_before=0,
            send_on=today,
            message=VAT_OVERDUE_REMINDER_MESSAGE.format(
                period=row.period,
                due_date=tax_deadline.due_date,
            ),
            tax_deadline_id=tax_deadline.id,
        )
        created += 1
        logger.info(
            "VAT compliance: created overdue reminder client_record_id=%d period=%s",
            row.client_record_id,
            row.period,
        )
    if created:
        logger.info("VAT compliance job: created %d reminder(s)", created)


async def daily_vat_compliance_job() -> None:
    """Create VAT_FILING reminders for overdue unfiled periods."""
    await _run_job("daily_vat_compliance_job", _vat_compliance_task)


async def daily_reminder_job() -> None:
    """Dispatch pending reminders once per day. Processed in batches of REMINDER_BATCH_SIZE."""
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
                page=1, page_size=REMINDER_BATCH_SIZE
            )

            sent = failed = 0
            for reminder in items:
                try:
                    # Claim before sending — prevents double-send if process restarts
                    # between send and mark_sent. Stuck PROCESSING rows are observable.
                    claimed = reminder_svc.claim_for_processing(reminder.id)
                    if not claimed:
                        continue
                    if reminder.business_id is not None:
                        delivered = notification_svc.notify_payment_reminder(
                            business_id=reminder.business_id,
                            reminder_text=reminder.message,
                        )
                    else:
                        delivered = notification_svc.notify_client_record_reminder(
                            client_record_id=reminder.client_record_id,
                            reminder_text=reminder.message,
                        )
                    if not delivered:
                        failed += 1
                        logger.warning(
                            "Reminder dispatch skipped/failed id=%d type=%s business_id=%s client_record_id=%s",
                            reminder.id,
                            reminder.reminder_type,
                            reminder.business_id,
                            reminder.client_record_id,
                        )
                        continue
                    reminder_svc.mark_sent(reminder.id, actor_id=_SYSTEM_ACTOR_ID)
                    sent += 1
                    logger.info(
                        "Reminder dispatched id=%d type=%s business_id=%s client_record_id=%s",
                        reminder.id,
                        reminder.reminder_type,
                        reminder.business_id,
                        reminder.client_record_id,
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
