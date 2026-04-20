"""Enrichment helpers for VAT work item query results."""

from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.users.repositories.user_repository import UserRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.vat_report_queries import (
    get_audit_trail,
    get_work_item,
    list_all_work_items,
    list_client_work_items,
    list_work_items_by_status,
)


def get_work_item_enriched(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    user_repo: UserRepository,
    item_id: int,
) -> dict:
    """Return work item + client/user enrichment data."""
    item = get_work_item(work_item_repo, item_id)
    client = client_repo.get_by_id(item.client_record_id)
    user_ids = [uid for uid in [item.assigned_to, item.filed_by] if uid]
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    user_map = {u.id: u.full_name for u in users}
    client_name = client.full_name if client else None
    return {
        "item": item,
        "office_client_number_map": {item.client_record_id: client.office_client_number if client else None},
        "name_map": {item.client_record_id: client_name},
        "id_number_map": {item.client_record_id: client.id_number if client else None},
        "status_map": {item.client_record_id: client.status if client else None},
        "user_map": user_map,
    }


def get_client_items_enriched(
    work_item_repo: VatWorkItemRepository,
    client_repo: ClientRepository,
    user_repo: UserRepository,
    client_record_id: int,
) -> dict:
    """Return client work items + enrichment data."""
    items = list_client_work_items(work_item_repo, client_record_id)
    client = client_repo.get_by_id(client_record_id)
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "office_client_number_map": {client_record_id: client.office_client_number if client else None},
        "name_map": {client_record_id: client.full_name if client else None},
        "id_number_map": {client_record_id: client.id_number if client else None},
        "status_map": {client_record_id: client.status if client else None},
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
    client_name: Optional[str] = None,
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
    client_record_ids = list({item.client_record_id for item in items})
    clients = client_repo.list_by_ids(client_record_ids)
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    users = user_repo.list_by_ids(user_ids) if user_ids else []
    return {
        "items": items,
        "total": total,
        "office_client_number_map": {c.id: c.office_client_number for c in clients},
        "name_map": {c.id: c.full_name for c in clients},
        "id_number_map": {c.id: c.id_number for c in clients},
        "status_map": {c.id: c.status for c in clients},
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
