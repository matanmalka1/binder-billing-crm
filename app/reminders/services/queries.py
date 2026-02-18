from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository


def get_reminders(
    reminder_repo: ReminderRepository,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int]:
    if status is None:
        return get_pending_reminders(reminder_repo, page=page, page_size=page_size)

    try:
        status_enum = ReminderStatus(status)
    except ValueError:
        raise ValueError(f"Invalid status: {status}. Must be one of: pending, sent, canceled")

    items = reminder_repo.list_by_status(status=status_enum, page=page, page_size=page_size)
    total = reminder_repo.count_by_status(status_enum)
    return items, total


def get_pending_reminders(
    reminder_repo: ReminderRepository,
    *,
    reference_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int]:
    if reference_date is None:
        reference_date = date.today()

    items = reminder_repo.list_pending_by_date(
        reference_date=reference_date,
        page=page,
        page_size=page_size,
    )
    total = reminder_repo.count_pending_by_date(reference_date)
    return items, total


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
