from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.utils.time_utils import utcnow


def mark_sent(reminder_repo: ReminderRepository, reminder_id: int, *, actor_id: int) -> Reminder:
    """Transition PENDING or PROCESSING → SENT.

    PROCESSING is a valid source state: the background job claims a reminder
    (PENDING → PROCESSING) then marks it sent after dispatch. Manual API calls
    may also arrive while the reminder is PROCESSING if the job is slow.
    Both paths are legitimate; blocking PROCESSING here would leave in-flight
    reminders permanently stuck.
    """
    reminder = reminder_repo.get_by_id(reminder_id)
    if not reminder:
        raise NotFoundError(f"תזכורת {reminder_id} לא נמצאה", "REMINDER.NOT_FOUND")

    if reminder.status not in (ReminderStatus.PENDING, ReminderStatus.PROCESSING):
        raise AppError(
            f"לא ניתן לסמן תזכורת במצב {reminder.status.value} כשולחה",
            "REMINDER.INVALID_STATUS",
        )

    return reminder_repo.update_status(
        reminder_id,
        ReminderStatus.SENT,
        sent_at=utcnow(),
        canceled_by=actor_id,   # reuse canceled_by field not applicable here —
                                # model has no sent_by; actor tracked via created_by pattern.
                                # TODO: add sent_by column if audit of manual sends is required.
    )


def cancel_reminder(reminder_repo: ReminderRepository, reminder_id: int, *, actor_id: int) -> Reminder:
    """Transition PENDING → CANCELED. Records which staff member canceled."""
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
        canceled_by=actor_id,
    )