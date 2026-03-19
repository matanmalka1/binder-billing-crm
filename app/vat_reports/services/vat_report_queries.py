"""Query helpers for VAT work items and invoices."""

from datetime import date, datetime, timezone
from typing import Optional

from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_enums import InvoiceType, VatWorkItemStatus
from app.vat_reports.repositories.vat_invoice_repository import VatInvoiceRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.users.repositories.user_repository import UserRepository


def _compute_deadline_fields(item) -> dict:
    """Derive submission_deadline, days_until_deadline, is_overdue from period."""
    try:
        year, month = int(item.period[:4]), int(item.period[5:7])
        dl = date(year + 1, 1, 15) if month == 12 else date(year, month + 1, 15)
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


def list_business_work_items(work_item_repo: VatWorkItemRepository, business_id: int):
    return work_item_repo.list_by_business(business_id)


def _resolve_business_ids(
    business_repo: BusinessRepository,
    business_name: Optional[str],
) -> Optional[list[int]]:
    if not business_name:
        return None
    businesses, _ = business_repo.list(search=business_name, page=1, page_size=10000)
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


def get_work_item_enriched(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    user_repo: UserRepository,
    item_id: int,
) -> dict:
    """Return work item + business/user enrichment data."""
    item = get_work_item(work_item_repo, item_id)
    business = business_repo.get_by_id(item.business_id)
    user_ids = [uid for uid in [item.assigned_to, item.filed_by] if uid]
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    user_map = {u.id: u.full_name for u in users}
    display_name = (business.business_name or business.client.full_name) if business else None
    return {
        "item": item,
        "name_map": {item.business_id: display_name},
        "status_map": {item.business_id: business.status.value if business else None},
        "user_map": user_map,
    }


def get_business_items_enriched(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    user_repo: UserRepository,
    business_id: int,
) -> dict:
    """Return business work items + enrichment data."""
    items = list_business_work_items(work_item_repo, business_id)
    business = business_repo.get_by_id(business_id)
    display_name = (business.business_name or business.client.full_name) if business else None
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "name_map": {business_id: display_name},
        "status_map": {business_id: business.status.value if business else None},
        "user_map": {u.id: u.full_name for u in users},
    }


def get_list_enriched(
    work_item_repo: VatWorkItemRepository,
    business_repo: BusinessRepository,
    user_repo: UserRepository,
    *,
    status_filter,
    page: int,
    page_size: int,
    period: Optional[str],
    business_name: Optional[str] = None,
) -> dict:
    """Return paginated work items + enrichment data."""
    if status_filter:
        items, total = list_work_items_by_status(
            work_item_repo, business_repo,
            status=status_filter, page=page, page_size=page_size,
            period=period, business_name=business_name,
        )
    else:
        items, total = list_all_work_items(
            work_item_repo, business_repo,
            page=page, page_size=page_size,
            period=period, business_name=business_name,
        )
    business_ids = list({item.business_id for item in items})
    businesses = business_repo.list_by_ids(business_ids)
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "total": total,
        "name_map": {
            b.id: (b.business_name or b.client.full_name) for b in businesses
        },
        "status_map": {b.id: b.status.value for b in businesses},
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