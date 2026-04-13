"""Query helpers for VAT work items and invoices."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.common.enums import SubmissionMethod
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    VAT_ONLINE_EXTENDED_DEADLINE_DAY,
    VAT_STATUTORY_DEADLINE_DAY,
)
from app.vat_reports.services.messages import VAT_ITEM_NOT_FOUND

logger = logging.getLogger(__name__)


def compute_deadline_fields(item, submission_method: Optional[SubmissionMethod] = None) -> dict:
    """Derive statutory and extended deadline fields from period.

    - statutory_deadline: 15th (legal baseline)
    - extended_deadline: 19th (digital filing extension)
    - submission_deadline: statutory by default; extended if submission_method is ONLINE
    - days_until_deadline: days remaining until submission_deadline
    - is_overdue: True if submission_deadline has passed
    """
    try:
        year, month = int(item.period[:4]), int(item.period[5:7])
        deadline_year = year + 1 if month == 12 else year
        deadline_month = 1 if month == 12 else month + 1
        statutory_deadline = date(
            deadline_year,
            deadline_month,
            VAT_STATUTORY_DEADLINE_DAY,
        )
        extended_deadline = date(
            deadline_year,
            deadline_month,
            VAT_ONLINE_EXTENDED_DEADLINE_DAY,
        )
        # Use extended deadline for online filers, statutory for manual filers
        submission_deadline = (
            extended_deadline
            if submission_method == SubmissionMethod.ONLINE
            else statutory_deadline
        )
        today = datetime.now(timezone.utc).date()
        days = (submission_deadline - today).days
        return {
            "submission_deadline": submission_deadline,
            "statutory_deadline": statutory_deadline,
            "extended_deadline": extended_deadline,
            "days_until_deadline": days,
            "is_overdue": days < 0,
        }
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to compute deadline for period '%s': %s", item.period, exc)
        return {
            "submission_deadline": None,
            "statutory_deadline": None,
            "extended_deadline": None,
            "days_until_deadline": None,
            "is_overdue": None,
        }


def get_work_item(work_item_repo: VatWorkItemRepository, item_id: int):
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(VAT_ITEM_NOT_FOUND.format(item_id=item_id), "VAT.NOT_FOUND")
    return item


def list_client_work_items(work_item_repo: VatWorkItemRepository, client_id: int):
    return work_item_repo.list_by_client(client_id)


def _resolve_client_ids_by_name(
    client_repo: ClientRepository,
    client_name: Optional[str],
) -> Optional[list[int]]:
    """Resolve client IDs from a name/id_number search against the clients table."""
    if not client_name:
        return None
    clients = client_repo.list(search=client_name, page=1, page_size=500)
    if len(clients) >= 500:
        logger.warning(
            "Client name search '%s' returned max results, may be truncated",
            client_name,
        )
    return [c.id for c in clients]


def list_work_items_by_status(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    status: VatWorkItemStatus,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    client_name: Optional[str] = None,
):
    client_ids = _resolve_client_ids_by_name(client_repo, client_name)
    if client_name and not client_ids:
        return [], 0
    items = work_item_repo.list_by_status(
        status, page=page, page_size=page_size, period=period, client_ids=client_ids
    )
    total = work_item_repo.count_by_status(status, period=period, client_ids=client_ids)
    return items, total


def list_all_work_items(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    client_name: Optional[str] = None,
):
    client_ids = _resolve_client_ids_by_name(client_repo, client_name)
    if client_name and not client_ids:
        return [], 0
    items = work_item_repo.list_all(
        page=page, page_size=page_size, period=period, client_ids=client_ids
    )
    total = work_item_repo.count_all(period=period, client_ids=client_ids)
    return items, total


def list_invoices(
    invoice_repo: VatInvoiceRepository,
    item_id: int,
    invoice_type: Optional[InvoiceType] = None,
):
    return invoice_repo.list_by_work_item(item_id, invoice_type=invoice_type)


def get_audit_trail(work_item_repo: VatWorkItemRepository, item_id: int):
    return work_item_repo.get_audit_trail(item_id)
