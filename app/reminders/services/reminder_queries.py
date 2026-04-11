from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List, Dict, TypedDict

from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.businesses.repositories.business_repository import BusinessRepository


class ReminderBusinessContext(TypedDict):
    business_name: str
    client_id: int
    client_name: str


def _build_name_map(
    business_repo: BusinessRepository,
    items: List[Reminder],
) -> Dict[int, ReminderBusinessContext]:
    business_ids = list({r.business_id for r in items if r.business_id is not None})
    businesses = business_repo.list_by_ids(business_ids)
    return {
        b.id: {
            "business_name": b.full_name,
            "client_id": b.client_id,
            "client_name": b.client.full_name if b.client else f"לקוח #{b.client_id}",
        }
        for b in businesses
    }


def get_reminders(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderBusinessContext]]:
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
) -> Tuple[List[Reminder], int, Dict[int, ReminderBusinessContext]]:
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
) -> Tuple[List[Reminder], int, Dict[int, ReminderBusinessContext]]:
    items = reminder_repo.list_by_business(business_id=business_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_business(business_id)
    return items, total, _build_name_map(business_repo, items)


def get_reminders_by_client(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    *,
    client_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderBusinessContext]]:
    items = reminder_repo.list_by_client(client_id=client_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_client(client_id)
    return items, total, _build_name_map(business_repo, items)


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
