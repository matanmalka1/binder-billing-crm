from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List, Dict

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.clients.repositories.client_repository import ClientRepository


def _build_name_map(
    client_repo: ClientRepository,
    items: List[Reminder],
) -> Dict[int, str]:
    client_ids = list({r.client_id for r in items})
    clients = client_repo.list_by_ids(client_ids)
    return {c.id: c.full_name for c in clients}


def get_reminders(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, str]]:
    if status is None:
        return get_pending_reminders(reminder_repo, client_repo, page=page, page_size=page_size)

    valid_statuses = {e.value for e in ReminderStatus}
    if status not in valid_statuses:
        raise AppError(
            f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: pending (ממתין), sent (נשלח), canceled (בוטל)",
            "REMINDER.INVALID_STATUS",
        )
    status_enum = ReminderStatus(status)

    items = reminder_repo.list_by_status(status=status_enum, page=page, page_size=page_size)
    total = reminder_repo.count_by_status(status_enum)
    return items, total, _build_name_map(client_repo, items)


def get_pending_reminders(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
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
    return items, total, _build_name_map(client_repo, items)


def get_reminders_by_client(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, str]]:
    items = reminder_repo.list_by_client(client_id=client_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_client(client_id)
    return items, total, _build_name_map(client_repo, items)


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
