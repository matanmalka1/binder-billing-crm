"""Query helpers for VAT work items and invoices."""

from typing import Optional

from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


def get_work_item(work_item_repo: VatWorkItemRepository, item_id: int):
    item = work_item_repo.get_by_id(item_id)
    if not item:
        raise ValueError(f"VAT work item {item_id} not found")
    return item


def list_client_work_items(work_item_repo: VatWorkItemRepository, client_id: int):
    return work_item_repo.list_by_client(client_id)


def list_work_items_by_status(
    work_item_repo: VatWorkItemRepository,
    status: VatWorkItemStatus,
    page: int = 1,
    page_size: int = 50,
):
    items = work_item_repo.list_by_status(status, page=page, page_size=page_size)
    total = work_item_repo.count_by_status(status)
    return items, total


def list_all_work_items(
    work_item_repo: VatWorkItemRepository,
    page: int = 1,
    page_size: int = 50,
):
    items = work_item_repo.list_all(page=page, page_size=page_size)
    total = work_item_repo.count_all()
    return items, total


def list_invoices(
    invoice_repo: VatInvoiceRepository,
    item_id: int,
    invoice_type: Optional[InvoiceType] = None,
):
    return invoice_repo.list_by_work_item(item_id, invoice_type=invoice_type)


def get_audit_trail(work_item_repo: VatWorkItemRepository, item_id: int):
    return work_item_repo.get_audit_trail(item_id)
