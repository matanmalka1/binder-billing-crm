from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time import utcnow


def mark_sent(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise NotFoundError(f"תזכורת {reminder_id} לא נמצאה", "REMINDER.NOT_FOUND")

    if reminder.status != ReminderStatus.PENDING:
        raise AppError(
            f"לא ניתן לסמן תזכורת במצב {reminder.status.value} כשולחה",
            "REMINDER.INVALID_STATUS",
        )

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.SENT,
        sent_at=utcnow(),
    )


def cancel_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise NotFoundError(f"תזכורת {reminder_id} לא נמצאה", "REMINDER.NOT_FOUND")

    if reminder.status != ReminderStatus.PENDING:
        raise AppError(
            f"לא ניתן לבטל תזכורת במצב {reminder.status.value}",
            "REMINDER.INVALID_STATUS",
        )

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.CANCELED,
        canceled_at=utcnow(),
    )
