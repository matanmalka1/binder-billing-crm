"""Query helpers for VAT work items and invoices."""

from datetime import date, datetime, timezone
from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


def _compute_deadline_fields(item) -> dict:
    """Derive submission_deadline, days_until_deadline, is_overdue from period."""
    try:
        year, month = int(item.period[:4]), int(item.period[5:7])
        # Next month
        if month == 12:
            dl = date(year + 1, 1, 15)
        else:
            dl = date(year, month + 1, 15)
        today = datetime.now(timezone.utc).date()
        days = (dl - today).days
        return {"submission_deadline": dl, "days_until_deadline": days, "is_overdue": days < 0}
    except Exception:
        return {"submission_deadline": None, "days_until_deadline": None, "is_overdue": None}


def get_work_item(work_item_repo: VatWorkItemRepository, item_id: int):
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise NotFoundError(f"פריט עבודה {item_id} למע\"מ לא נמצא", "VAT.NOT_FOUND")
    return item


def list_client_work_items(work_item_repo: VatWorkItemRepository, client_id: int):
    return work_item_repo.list_by_client(client_id)


def _resolve_client_ids(
    client_repo: ClientRepository,
    client_name: Optional[str],
) -> Optional[list[int]]:
    if not client_name:
        return None
    clients, _ = client_repo.search(client_name=client_name, page=1, page_size=10000)
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
    client_ids = _resolve_client_ids(client_repo, client_name)
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
    client_ids = _resolve_client_ids(client_repo, client_name)
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
