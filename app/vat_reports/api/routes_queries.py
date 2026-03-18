"""Routes: read-only queries — work items, audit trail."""

from typing import Optional

from fastapi import APIRouter, Query

from app.users.api.deps import CurrentUser, DBSession
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services.vat_report_queries import _compute_deadline_fields
from app.vat_reports.schemas import (
    VatAuditLogResponse,
    VatAuditTrailResponse,
    VatWorkItemListResponse,
    VatWorkItemResponse,
)
from app.vat_reports.services.vat_report_service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


def _serialize(item, name_map: dict, status_map: dict, user_map: dict) -> VatWorkItemResponse:
    data = VatWorkItemResponse.model_validate(item)
    data.client_name = name_map.get(item.client_id)
    data.client_status = status_map.get(item.client_id)
    deadline = _compute_deadline_fields(item)
    data.submission_deadline = deadline["submission_deadline"]
    data.days_until_deadline = deadline["days_until_deadline"]
    data.is_overdue = deadline["is_overdue"]
    data.assigned_to_name = user_map.get(item.assigned_to) if item.assigned_to else None
    data.filed_by_name = user_map.get(item.filed_by) if item.filed_by else None
    return data


@router.get("/work-items/{item_id}", response_model=VatWorkItemResponse)
def get_work_item(item_id: int, db: DBSession, current_user: CurrentUser):
    """Get a single work item by ID."""
    service = VatReportService(db)
    enriched = service.get_work_item_enriched(item_id)
    return _serialize(
        enriched["item"],
        enriched["name_map"],
        enriched["status_map"],
        enriched["user_map"],
    )


@router.get("/clients/{client_id}/work-items", response_model=VatWorkItemListResponse)
def list_client_work_items(client_id: int, db: DBSession, current_user: CurrentUser):
    """List all VAT work items for a client."""
    service = VatReportService(db)
    enriched = service.get_client_items_enriched(client_id)
    items = [
        _serialize(i, enriched["name_map"], enriched["status_map"], enriched["user_map"])
        for i in enriched["items"]
    ]
    return VatWorkItemListResponse(items=items, total=len(items))


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
    """List work items filtered by status with pagination."""
    service = VatReportService(db)
    enriched = service.get_list_enriched(
        status_filter=status_filter, page=page, page_size=page_size,
        period=period, client_name=client_name,
    )
    items = [
        _serialize(i, enriched["name_map"], enriched["status_map"], enriched["user_map"])
        for i in enriched["items"]
    ]
    return VatWorkItemListResponse(items=items, total=enriched["total"])


@router.get("/work-items/{item_id}/audit", response_model=VatAuditTrailResponse)
def get_audit_trail(item_id: int, db: DBSession, current_user: CurrentUser):
    """Get the full audit trail for a work item."""
    service = VatReportService(db)
    enriched = service.get_audit_trail_enriched(item_id)
    items = []
    for e in enriched["entries"]:
        row = VatAuditLogResponse.model_validate(e)
        row.performed_by_name = enriched["user_map"].get(e.performed_by)
        items.append(row)
    return VatAuditTrailResponse(items=items)