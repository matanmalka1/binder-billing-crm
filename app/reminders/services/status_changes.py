from __future__ import annotations

from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time import utcnow


def mark_sent(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise ValueError(f"תזכורת {reminder_id} לא נמצאה")

    if reminder.status != ReminderStatus.PENDING:
        raise ValueError(f"לא ניתן לסמן תזכורת במצב {reminder.status.value} כשולחה")

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.SENT,
        sent_at=utcnow(),
    )


def cancel_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Reminder:
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise ValueError(f"תזכורת {reminder_id} לא נמצאה")

    if reminder.status != ReminderStatus.PENDING:
        raise ValueError(f"לא ניתן לבטל תזכורת במצב {reminder.status.value}")

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.CANCELED,
        canceled_at=utcnow(),
    )
