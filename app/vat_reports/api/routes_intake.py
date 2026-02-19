"""Routes: work item creation and material intake."""

from fastapi import APIRouter, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession
from app.users.models.user import UserRole
from app.vat_reports.schemas import (
    VatWorkItemCreateRequest,
    VatWorkItemResponse,
)
from app.vat_reports.services.service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


@router.post("/work-items", response_model=VatWorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_work_item(
    request: VatWorkItemCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a VAT work item for a client / period.

    Accessible by: receptionist, secretary, advisor.
    """
    service = VatReportService(db)
    try:
        item = service.create_work_item(
            client_id=request.client_id,
            period=request.period,
            created_by=current_user.id,
            assigned_to=request.assigned_to,
            mark_pending=request.mark_pending,
            pending_materials_note=request.pending_materials_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item


@router.post(
    "/work-items/{item_id}/materials-complete",
    response_model=VatWorkItemResponse,
)
def mark_materials_complete(
    item_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Mark materials as complete: PENDING_MATERIALS → MATERIAL_RECEIVED.

    Accessible by: receptionist, secretary, advisor.
    """
    service = VatReportService(db)
    try:
        item = service.mark_materials_complete(
            item_id=item_id,
            performed_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item
