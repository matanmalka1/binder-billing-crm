"""Routes: read-only queries — work items, audit trail."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.vat_reports.api.serializers import serialize_enriched_work_item
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.schemas.vat_audit import VatAuditLogResponse, VatAuditTrailResponse
from app.vat_reports.schemas.vat_report import (
    VatPeriodOptionsResponse,
    VatWorkItemListResponse,
    VatWorkItemLookupResponse,
    VatWorkItemResponse,
)
from app.vat_reports.services.vat_report_service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


@router.get(
    "/work-items/lookup",
    response_model=Optional[VatWorkItemLookupResponse],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def lookup_work_item(
    db: DBSession,
    current_user: CurrentUser,
    client_id: int = Query(...),
    period: str = Query(...),
):
    """Lookup a VAT work item by client + period. Returns null if not found."""
    service = VatReportService(db)
    item = service.get_work_item_by_client_period(client_id, period)
    if not item:
        return None
    return VatWorkItemLookupResponse.model_validate(item)


@router.get(
    "/clients/{client_id}/period-options",
    response_model=VatPeriodOptionsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_period_options(
    client_id: int,
    db: DBSession,
    current_user: CurrentUser,
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
):
    """Return selectable VAT periods for a client based on their reporting frequency."""
    service = VatReportService(db)
    return service.get_period_options(client_id=client_id, year=year)


@router.get(
    "/work-items/{item_id}",
    response_model=VatWorkItemResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_work_item(item_id: int, db: DBSession, current_user: CurrentUser):
    """Get a single work item by ID."""
    service = VatReportService(db)
    enriched = service.get_work_item_enriched(item_id)
    return serialize_enriched_work_item(
        enriched["item"],
        office_client_number_map=enriched["office_client_number_map"],
        name_map=enriched["name_map"],
        id_number_map=enriched["id_number_map"],
        status_map=enriched["status_map"],
        user_map=enriched["user_map"],
    )


@router.get(
    "/clients/{client_id}/work-items",
    response_model=VatWorkItemListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_client_work_items(client_id: int, db: DBSession, current_user: CurrentUser):
    """List all VAT work items for a client."""
    service = VatReportService(db)
    enriched = service.get_client_items_enriched(client_id)
    items = [
        serialize_enriched_work_item(
            i,
            office_client_number_map=enriched["office_client_number_map"],
            name_map=enriched["name_map"],
            id_number_map=enriched["id_number_map"],
            status_map=enriched["status_map"],
            user_map=enriched["user_map"],
        )
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
    client_name: Optional[str] = Query(None),
):
    """List work items filtered by status with pagination."""
    service = VatReportService(db)
    enriched = service.get_list_enriched(
        status_filter=status_filter, page=page, page_size=page_size,
        period=period, client_name=client_name,
    )
    items = [
        serialize_enriched_work_item(
            i,
            office_client_number_map=enriched["office_client_number_map"],
            name_map=enriched["name_map"],
            id_number_map=enriched["id_number_map"],
            status_map=enriched["status_map"],
            user_map=enriched["user_map"],
        )
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
