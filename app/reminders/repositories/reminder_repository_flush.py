"""Flush-only (no commit) write helpers — used by deadline sync to batch mutations."""
from typing import Optional

from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository_read import ReminderRepositoryRead
from app.utils.time_utils import utcnow


class ReminderRepositoryFlush(ReminderRepositoryRead):
    """Flush-only mutations for use inside a caller-managed transaction."""

    def cancel_pending_by_tax_deadline_flush(self, tax_deadline_id: int) -> int:
        """Cancel all PENDING reminders linked to a tax deadline (flush, no commit)."""
        now = utcnow()
        rows = (
            self.db.query(Reminder)
            .filter(
                Reminder.tax_deadline_id == tax_deadline_id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.deleted_at.is_(None),
            )
            .all()
        )
        for r in rows:
            r.status = ReminderStatus.CANCELED
            r.canceled_at = now
        if rows:
            self.db.flush()
        return len(rows)

    def create_flush(
        self,
        reminder_type: ReminderType,
        target_date,
        days_before: int,
        send_on,
        message: str,
        business_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tax_deadline_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Reminder:
        """Insert a new reminder and flush (no commit). Use only inside a sync transaction."""
        if (business_id is None) == (client_id is None):
            raise AppError(
                "תזכורת חייבת לשייך לעסק או ללקוח — לא לשניהם ולא לאף אחד",
                "REMINDER.INVALID_OWNER",
            )
        reminder = Reminder(
            business_id=business_id,
            client_id=client_id,
            reminder_type=reminder_type,
            target_date=target_date,
            days_before=days_before,
            send_on=send_on,
            message=message,
            status=ReminderStatus.PENDING,
            tax_deadline_id=tax_deadline_id,
            created_by=created_by,
        )
        self.db.add(reminder)
        self.db.flush()
        return reminder
