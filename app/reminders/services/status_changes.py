from __future__ import annotations

from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time import utcnow


def mark_sent(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise ValueError(f"Reminder {reminder_id} not found")

    if reminder.status != ReminderStatus.PENDING:
        raise ValueError(f"Cannot mark {reminder.status.value} reminder as sent")

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.SENT,
        sent_at=utcnow(),
    )


def cancel_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise ValueError(f"Reminder {reminder_id} not found")

    if reminder.status != ReminderStatus.PENDING:
        raise ValueError(f"Cannot cancel {reminder.status.value} reminder")

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.CANCELED,
        canceled_at=utcnow(),
    )
