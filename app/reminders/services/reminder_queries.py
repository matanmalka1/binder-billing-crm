from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple, TypedDict

from app.core.exceptions import AppError
from app.reminders.models.reminder import Reminder, ReminderStatus
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository

_DEADLINE_TYPE_LABELS: Dict[str, str] = {
    "vat":                'מועד מע"מ מתקרב',
    "advance_payment":    "מועד מקדמות מתקרב",
    "national_insurance": "מועד ביטוח לאומי מתקרב",
    "annual_report":      "מועד דוח שנתי מתקרב",
    "other":              "מועד מס מתקרב",
}


class ReminderContext(TypedDict):
    client_record_id: int
    client_name: str
    client_id_number: Optional[str]
    office_client_number: Optional[int]
    business_id: Optional[int]
    business_name: Optional[str]
    display_label: Optional[str]


def _build_context_map(
    client_repo: ClientRepository,
    business_repo: BusinessRepository,
    items: List[Reminder],
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
) -> Dict[int, ReminderContext]:
    """Build a reminder_id → context map for all items."""
    client_record_ids = list({r.client_record_id for r in items})
    business_ids = list({r.business_id for r in items if r.business_id is not None})

    clients = {c.id: c for c in client_repo.list_by_ids(client_record_ids)}
    businesses = {b.id: b for b in business_repo.list_by_ids(business_ids)} if business_ids else {}

    # Resolve display_label for reminders linked to a tax_deadline
    deadline_label_map: Dict[int, str] = {}
    if tax_deadline_repo is not None:
        td_ids = list({r.tax_deadline_id for r in items if r.tax_deadline_id is not None})
        for td_id in td_ids:
            deadline = tax_deadline_repo.get_by_id(td_id)
            if deadline:
                deadline_label_map[td_id] = _DEADLINE_TYPE_LABELS.get(
                    deadline.deadline_type.value, "מועד מס מתקרב"
                )

    result: Dict[int, ReminderContext] = {}
    for r in items:
        # client_record_id == legacy client_record_id (same PK by migration convention)
        client = clients.get(r.client_record_id)
        business = businesses.get(r.business_id) if r.business_id else None
        display_label = deadline_label_map.get(r.tax_deadline_id) if r.tax_deadline_id else None
        result[r.id] = ReminderContext(
            client_record_id=r.client_record_id,
            client_name=client.full_name if client else f"לקוח #{r.client_record_id}",
            client_id_number=client.id_number if client else None,
            office_client_number=client.office_client_number if client else None,
            business_id=r.business_id,
            business_name=business.business_name if business else None,
            display_label=display_label,
        )
    return result


def get_reminders(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    if status is None:
        return get_pending_reminders(reminder_repo, client_repo, business_repo, tax_deadline_repo, page=page, page_size=page_size)

    valid_statuses = {e.value for e in ReminderStatus}
    if status not in valid_statuses:
        raise AppError(
            f"סטטוס לא חוקי: {status}. חייב להיות אחד מהבאים: {', '.join(valid_statuses)}",
            "REMINDER.INVALID_STATUS",
        )
    status_enum = ReminderStatus(status)
    items = reminder_repo.list_by_status(status=status_enum, page=page, page_size=page_size)
    total = reminder_repo.count_by_status(status_enum)
    return items, total, _build_context_map(client_repo, business_repo, items, tax_deadline_repo)


def get_pending_reminders(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    reference_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    if reference_date is None:
        reference_date = date.today()

    items = reminder_repo.list_pending_by_date(reference_date=reference_date, page=page, page_size=page_size)
    total = reminder_repo.count_pending_by_date(reference_date)
    return items, total, _build_context_map(client_repo, business_repo, items, tax_deadline_repo)


def get_reminders_by_business(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    business_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    items = reminder_repo.list_by_business(business_id=business_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_business(business_id)
    return items, total, _build_context_map(client_repo, business_repo, items, tax_deadline_repo)


def get_reminders_by_client(
    reminder_repo: ReminderRepository,
    client_repo: ClientRepository,
    business_repo: BusinessRepository,
    tax_deadline_repo: Optional[TaxDeadlineRepository] = None,
    *,
    client_record_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int, Dict[int, ReminderContext]]:
    client_record_id = ClientRecordRepository(reminder_repo.db).get_by_id(client_record_id).id
    items = reminder_repo.list_by_client_record(client_record_id, page=page, page_size=page_size)
    total = reminder_repo.count_by_client_record(client_record_id)
    return items, total, _build_context_map(client_repo, business_repo, items, tax_deadline_repo)


def get_reminder(reminder_repo: ReminderRepository, reminder_id: int) -> Optional[Reminder]:
    return reminder_repo.get_by_id(reminder_id)
