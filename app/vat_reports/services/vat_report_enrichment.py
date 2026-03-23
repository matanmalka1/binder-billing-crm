"""Enrichment helpers for VAT work item query results."""

from typing import Optional

from app.businesses.repositories.business_repository import BusinessRepository
from app.users.repositories.user_repository import UserRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.vat_report_queries import (
    get_audit_trail,
    get_work_item,
    list_all_work_items,
    list_business_work_items,
    list_work_items_by_status,
)


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
        "status_map": {item.business_id: business.status if business else None},
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
        "status_map": {business_id: business.status if business else None},
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
        "status_map": {b.id: b.status for b in businesses},
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
