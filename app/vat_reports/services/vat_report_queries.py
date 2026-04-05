"""Query helpers for VAT work items and invoices."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.constants import (
    VAT_ONLINE_EXTENDED_DEADLINE_DAY,
    VAT_STATUTORY_DEADLINE_DAY,
)

logger = logging.getLogger(__name__)


def compute_deadline_fields(item) -> dict:
    """Derive statutory and extended deadline fields from period."""
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
        today = datetime.now(timezone.utc).date()
        days = (statutory_deadline - today).days
        return {
            "submission_deadline": statutory_deadline,
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
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")
    return item


def list_business_work_items(work_item_repo: VatWorkItemRepository, business_id: int):
    return work_item_repo.list_by_business(business_id)


def _resolve_business_ids(
    business_repo: BusinessRepository,
    business_name: Optional[str],
) -> Optional[list[int]]:
    if not business_name:
        return None
    businesses = business_repo.list(search=business_name, page=1, page_size=500)
    if len(businesses) >= 500:
        logger.warning(
            "Business name search '%s' returned max results, may be truncated",
            business_name,
        )
    return [b.id for b in businesses]


def list_work_items_by_status(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    status: VatWorkItemStatus,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    business_name: Optional[str] = None,
):
    business_ids = _resolve_business_ids(business_repo, business_name)
    if business_name and not business_ids:
        return [], 0
    items = work_item_repo.list_by_status(
        status, page=page, page_size=page_size, period=period, business_ids=business_ids
    )
    total = work_item_repo.count_by_status(status, period=period, business_ids=business_ids)
    return items, total


def list_all_work_items(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    page: int = 1,
    page_size: int = 50,
    period: Optional[str] = None,
    business_name: Optional[str] = None,
):
    business_ids = _resolve_business_ids(business_repo, business_name)
    if business_name and not business_ids:
        return [], 0
    items = work_item_repo.list_all(
        page=page, page_size=page_size, period=period, business_ids=business_ids
    )
    total = work_item_repo.count_all(period=period, business_ids=business_ids)
    return items, total


def list_invoices(
    invoice_repo: VatInvoiceRepository,
    item_id: int,
    invoice_type: Optional[InvoiceType] = None,
):
    return invoice_repo.list_by_work_item(item_id, invoice_type=invoice_type)


def get_audit_trail(work_item_repo: VatWorkItemRepository, item_id: int):
    return work_item_repo.get_audit_trail(item_id)
