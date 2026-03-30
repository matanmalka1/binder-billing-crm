"""Routes: read-only queries — work items, audit trail."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.services.vat_report_queries import compute_deadline_fields
from app.vat_reports.schemas import (
    VatAuditLogResponse,
    VatAuditTrailResponse,
    VatPeriodOptionsResponse,
    VatWorkItemListResponse,
    VatWorkItemLookupResponse,
    VatWorkItemResponse,
)
from app.vat_reports.services.vat_report_service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


def _serialize(item, name_map: dict, status_map: dict, user_map: dict, client_map: dict | None = None) -> VatWorkItemResponse:
    data = VatWorkItemResponse.model_validate(item)
    data.client_id = client_map.get(item.business_id) if client_map else None
    data.business_name = name_map.get(item.business_id)
    data.business_status = status_map.get(item.business_id)
    deadline = compute_deadline_fields(item)
    data.submission_deadline = deadline["submission_deadline"]
    data.days_until_deadline = deadline["days_until_deadline"]
    data.is_overdue = deadline["is_overdue"]
    data.assigned_to_name = user_map.get(item.assigned_to) if item.assigned_to else None
    data.filed_by_name = user_map.get(item.filed_by) if item.filed_by else None
    return data


@router.get(
    "/work-items/lookup",
    response_model=Optional[VatWorkItemLookupResponse],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def lookup_work_item(
    db: DBSession,
    current_user: CurrentUser,
    business_id: int = Query(...),
    period: str = Query(...),
):
    """Lookup a VAT work item by business + period. Returns null if not found."""
    service = VatReportService(db)
    item = service.get_work_item_by_business_period(business_id, period)
    if not item:
        return None
    return VatWorkItemLookupResponse.model_validate(item)


@router.get(
    "/businesses/{business_id}/period-options",
    response_model=VatPeriodOptionsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_period_options(
    business_id: int,
    db: DBSession,
    current_user: CurrentUser,
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
):
    """Return selectable VAT periods for a business based on its reporting frequency."""
    service = VatReportService(db)
    return service.get_period_options(business_id=business_id, year=year)


@router.get(
    "/work-items/{item_id}",
    response_model=VatWorkItemResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_work_item(item_id: int, db: DBSession, current_user: CurrentUser):
    """Get a single work item by ID."""
    service = VatReportService(db)
    enriched = service.get_work_item_enriched(item_id)
    return _serialize(
        enriched["item"],
        enriched["name_map"],
        enriched["status_map"],
        enriched["user_map"],
        enriched.get("client_map"),
    )


@router.get(
    "/businesses/{business_id}/work-items",
    response_model=VatWorkItemListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_business_work_items(business_id: int, db: DBSession, current_user: CurrentUser):
    """List all VAT work items for a business."""
    service = VatReportService(db)
    enriched = service.get_business_items_enriched(business_id)
    cm = enriched.get("client_map")
    items = [
        _serialize(i, enriched["name_map"], enriched["status_map"], enriched["user_map"], cm)
        for i in enriched["items"]
    ]
    return VatWorkItemListResponse(items=items, total=len(items))


@router.get(
    "/work-items",
    response_model=VatWorkItemListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_work_items(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: Optional[VatWorkItemStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    period: Optional[str] = Query(None),
    business_name: Optional[str] = Query(None),
):
    """List work items filtered by status with pagination."""
    service = VatReportService(db)
    enriched = service.get_list_enriched(
        status_filter=status_filter, page=page, page_size=page_size,
        period=period, business_name=business_name,
    )
    cm = enriched.get("client_map")
    items = [
        _serialize(i, enriched["name_map"], enriched["status_map"], enriched["user_map"], cm)
        for i in enriched["items"]
    ]
    return VatWorkItemListResponse(items=items, total=enriched["total"])


@router.get(
    "/work-items/{item_id}/audit",
    response_model=VatAuditTrailResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
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
