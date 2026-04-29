from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.reminders.services.reminder_context import ReminderContext, build_context_map
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.utils.time_utils import israel_today

READY_DUE_FILTER = "ready"
LEGACY_ACTIONABLE_DUE_FILTER = "actionable"
VALID_DUE_FILTERS = {READY_DUE_FILTER, LEGACY_ACTIONABLE_DUE_FILTER}


def get_reminders(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    status: Optional[str] = None,
    due: Optional[str] = None,
    created_before: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    if due is not None and due not in VALID_DUE_FILTERS:
        raise AppError("סינון מועד לא חוקי", "REMINDER.INVALID_DUE_FILTER")

    if due in VALID_DUE_FILTERS or status is None:
        return get_pending_reminders(
            reminder_repo,
            business_repo,
            tax_deadline_repo,
            page=page,
            page_size=page_size,
        )

    valid_statuses = {e.value for e in ReminderStatus}
    if status not in valid_statuses:
        raise AppError(
            f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: {', '.join(valid_statuses)}",
            "REMINDER.INVALID_STATUS",
        )
    status_enum = ReminderStatus(status)
    items = reminder_repo.list_by_status(status=status_enum, page=page, page_size=page_size, created_before=created_before)
    total = reminder_repo.count_by_status(status_enum, created_before=created_before)
    return items, total, build_context_map(reminder_repo.db, business_repo, items, tax_deadline_repo)


def get_pending_reminders(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    reference_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    if reference_date is None:
        reference_date = israel_today()

    items = reminder_repo.list_pending_by_date(reference_date=reference_date, page=page, page_size=page_size)
    total = reminder_repo.count_pending_by_date(reference_date)
    return items, total, build_context_map(reminder_repo.db, business_repo, items, tax_deadline_repo)


def get_reminders_by_business(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    business_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    items = reminder_repo.list_by_business(business_id=business_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_business(business_id)
    return items, total, build_context_map(reminder_repo.db, business_repo, items, tax_deadline_repo)


def get_reminders_by_client(
    reminder_repo: ReminderRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    client_record_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    client_record_id = int(ClientRecordRepository(reminder_repo.db).get_by_id(client_record_id).id)
    items = reminder_repo.list_by_client_record(client_record_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_client_record(client_record_id)
    return items, total, build_context_map(reminder_repo.db, business_repo, items, tax_deadline_repo)


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
