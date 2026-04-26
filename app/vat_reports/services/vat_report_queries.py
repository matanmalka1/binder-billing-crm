"""Query helpers for VAT work items and invoices."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
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


def list_client_work_items(work_item_repo: VatWorkItemRepository, client_record_id: int):
    return work_item_repo.list_by_client_record(client_record_id)

def _resolve_client_ids_by_name(
    db,
    client_name: Optional[str],
) -> Optional[list[int]]:
    """Resolve client record IDs from a name/id_number search against ClientRecord + LegalEntity."""
    if not client_name:
        return None
    client_records, total = ClientRecordRepository(db).search(
        query=client_name,
        page=1,
        page_size=500,
    )
    if total >= 500:
        logger.warning(
            "Client name search '%s' returned max results, may be truncated",
            client_name,
        )
    return [record.id for record in client_records]

def list_work_items_by_status(
    work_item_repo: VatWorkItemRepository,
    status: VatWorkItemStatus,
    db=None,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    client_name: Optional[str] = None,
    client_repo=None,
):
    search_source = db or getattr(client_repo, "db", None)
    client_record_ids = _resolve_client_ids_by_name(search_source, client_name) if search_source else None
    if client_record_ids is None and client_name and client_repo is not None:
        client_record_ids = [record.id for record in client_repo.list(search=client_name)]
    if client_name and not client_record_ids:
        return [], 0
    items = work_item_repo.list_by_status(
        status, page=page, page_size=page_size, period=period, client_record_ids=client_record_ids
    )
    total = work_item_repo.count_by_status(
        status, period=period, client_record_ids=client_record_ids
    )
    return items, total

def list_all_work_items(
    work_item_repo: VatWorkItemRepository,
    db=None,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    client_name: Optional[str] = None,
    client_repo=None,
):
    search_source = db or getattr(client_repo, "db", None)
    client_record_ids = _resolve_client_ids_by_name(search_source, client_name) if search_source else None
    if client_record_ids is None and client_name and client_repo is not None:
        client_record_ids = [record.id for record in client_repo.list(search=client_name)]
    if client_name and not client_record_ids:
        return [], 0
    items = work_item_repo.list_all(
        page=page, page_size=page_size, period=period, client_record_ids=client_record_ids
    )
    total = work_item_repo.count_all(period=period, client_record_ids=client_record_ids)
    return items, total

def list_invoices(
    invoice_repo: VatInvoiceRepository,
    item_id: int,
    invoice_type: Optional[InvoiceType] = None,
):
    return invoice_repo.list_by_work_item(item_id, invoice_type=invoice_type)

def get_audit_trail(work_item_repo: VatWorkItemRepository, item_id: int, limit: int, offset: int):
    return work_item_repo.get_audit_trail(item_id, limit, offset)

def count_audit_trail(work_item_repo: VatWorkItemRepository, item_id: int):
    return work_item_repo.count_audit_trail(item_id)
