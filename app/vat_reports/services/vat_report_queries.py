"""Query helpers for VAT work items and invoices."""

from datetime import date, datetime, timezone
from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.clients.repositories.client_repository import ClientRepository
from app.users.repositories.user_repository import UserRepository



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

def get_work_item_enriched(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    user_repo: UserRepository,
    item_id: int,
) -> dict:
    """Return work item + client/user enrichment data."""
    item = get_work_item(work_item_repo, item_id)
    client = client_repo.get_by_id(item.client_id)
    user_ids = [uid for uid in [item.assigned_to, item.filed_by] if uid]
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    user_map = {u.id: u.full_name for u in users}
    return {
        "item": item,
        "name_map": {item.client_id: client.full_name if client else None},
        "status_map": {item.client_id: client.status.value if client else None},
        "user_map": user_map,
    }


def get_client_items_enriched(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    user_repo: UserRepository,
    client_id: int,
) -> dict:
    """Return client work items + enrichment data."""
    items = list_client_work_items(work_item_repo, client_id)
    client = client_repo.get_by_id(client_id)
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "name_map": {client_id: client.full_name if client else None},
        "status_map": {client_id: client.status.value if client else None},
        "user_map": {u.id: u.full_name for u in users},
    }


def get_list_enriched(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    user_repo: UserRepository,
    *,
    status_filter,
    page: int,
    page_size: int,
    period: Optional[str],
    client_name: Optional[str],
) -> dict:
    """Return paginated work items + enrichment data."""
    if status_filter:
        items, total = list_work_items_by_status(
            work_item_repo, client_repo,
            status=status_filter, page=page, page_size=page_size,
            period=period, client_name=client_name,
        )
    else:
        items, total = list_all_work_items(
            work_item_repo, client_repo,
            page=page, page_size=page_size,
            period=period, client_name=client_name,
        )
    client_ids = list({item.client_id for item in items})
    clients = client_repo.list_by_ids(client_ids)
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "total": total,
        "name_map": {c.id: c.full_name for c in clients},
        "status_map": {c.id: c.status.value for c in clients},
        "user_map": {u.id: u.full_name for u in users},
    }


def get_audit_trail_enriched(
    work_item_repo: VatWorkItemRepository,
    user_repo: UserRepository,
    item_id: int,
) -> dict:
    entries = get_audit_trail(work_item_repo, item_id)
    user_ids = list({e.performed_by for e in entries})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {"entries": entries, "user_map": {u.id: u.full_name for u in users}}