"""Routes: read-only queries — work items, audit trail."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession
from app.users.models.user import User
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.schemas import (
    VatAuditLogResponse,
    VatAuditTrailResponse,
    VatWorkItemListResponse,
    VatWorkItemResponse,
)
from app.vat_reports.services.vat_report_service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


def _serialize_with_name(item, name_map: dict) -> VatWorkItemResponse:
    """Build a VatWorkItemResponse enriched with the client's full name."""
    data = VatWorkItemResponse.model_validate(item)
    data.client_name = name_map.get(item.client_id)
    return data


def _build_user_map(db, user_ids: list[int]) -> dict[int, str]:
    """Return a mapping of user_id → full_name for the given IDs."""
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return {u.id: u.full_name for u in users}


def _enrich_user_names(serialized: list[VatWorkItemResponse], user_map: dict) -> None:
    """Populate assigned_to_name / filed_by_name in-place."""
    for item in serialized:
        item.assigned_to_name = user_map.get(item.assigned_to) if item.assigned_to else None
        item.filed_by_name = user_map.get(item.filed_by) if item.filed_by else None


@router.get("/work-items/{item_id}", response_model=VatWorkItemResponse)
def get_work_item(
    item_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a single work item by ID."""
    service = VatReportService(db)
    item = service.get_work_item(item_id)
    client = service.client_repo.get_by_id(item.client_id)
    result = _serialize_with_name(item, {item.client_id: client.full_name if client else None})
    user_ids = [uid for uid in [item.assigned_to, item.filed_by] if uid is not None]
    user_map = _build_user_map(db, user_ids)
    result.assigned_to_name = user_map.get(item.assigned_to)
    result.filed_by_name = user_map.get(item.filed_by)
    return result


@router.get("/clients/{client_id}/work-items", response_model=VatWorkItemListResponse)
def list_client_work_items(
    client_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """List all VAT work items for a client."""
    service = VatReportService(db)
    items = service.list_client_work_items(client_id)
    client = service.client_repo.get_by_id(client_id)
    client_name = client.full_name if client else None
    name_map = {client_id: client_name}
    serialized = [_serialize_with_name(item, name_map) for item in items]
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    _enrich_user_names(serialized, _build_user_map(db, user_ids))
    return VatWorkItemListResponse(items=serialized, total=len(serialized))


@router.get("/work-items", response_model=VatWorkItemListResponse)
def list_work_items(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: Optional[VatWorkItemStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    period: Optional[str] = Query(None),
    client_name: Optional[str] = Query(None),
):
    """List work items filtered by status with pagination. Returns all when no filter."""
    service = VatReportService(db)
    if status_filter:
        items, total = service.list_work_items_by_status(
            status=status_filter, page=page, page_size=page_size,
            period=period, client_name=client_name,
        )
    else:
        items, total = service.list_all_work_items(
            page=page, page_size=page_size, period=period, client_name=client_name,
        )

    client_ids = list({item.client_id for item in items})
    clients = service.client_repo.list_by_ids(client_ids)
    name_map = {c.id: c.full_name for c in clients}
    serialized = [_serialize_with_name(item, name_map) for item in items]
    user_ids = list({uid for item in items for uid in [item.assigned_to, item.filed_by] if uid})
    _enrich_user_names(serialized, _build_user_map(db, user_ids))
    return VatWorkItemListResponse(items=serialized, total=total)


@router.get("/work-items/{item_id}/audit", response_model=VatAuditTrailResponse)
def get_audit_trail(
    item_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get the full audit trail for a work item."""
    service = VatReportService(db)
    entries = service.get_audit_trail(item_id)
    user_ids = list({e.performed_by for e in entries})
    user_map = _build_user_map(db, user_ids)
    items = []
    for e in entries:
        row = VatAuditLogResponse.model_validate(e)
        row.performed_by_name = user_map.get(e.performed_by)
        items.append(row)
    return VatAuditTrailResponse(items=items)
