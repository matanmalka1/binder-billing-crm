from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List, Dict

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.businesses.repositories.business_repository import BusinessRepository


def _build_name_map(
    business_repo: BusinessRepository,
    items: List[Reminder],
) -> Dict[int, str]:
    business_ids = list({r.business_id for r in items})
    businesses = business_repo.list_by_ids(business_ids)
    return {b.id: b.full_name for b in businesses}


def get_reminders(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, str]]:
    if status is None:
        return get_pending_reminders(reminder_repo, business_repo, page=page, page_size=page_size)

    valid_statuses = {e.value for e in ReminderStatus}
    if status not in valid_statuses:
        raise AppError(
            f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: pending (ממתין), sent (נשלח), canceled (בוטל)",
            "REMINDER.INVALID_STATUS",
        )
    status_enum = ReminderStatus(status)

    items = reminder_repo.list_by_status(status=status_enum, page=page, page_size=page_size)
    total = reminder_repo.count_by_status(status_enum)
    return items, total, _build_name_map(business_repo, items)


def get_pending_reminders(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    reference_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, str]]:
    if reference_date is None:
        reference_date = date.today()

    items = reminder_repo.list_pending_by_date(
        reference_date=reference_date,
        page=page,
        page_size=page_size,
    )
    total = reminder_repo.count_pending_by_date(reference_date)
    return items, total, _build_name_map(business_repo, items)


def get_reminders_by_business(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    business_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, str]]:
    items = reminder_repo.list_by_business(business_id=business_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_business(business_id)
    return items, total, _build_name_map(business_repo, items)


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
