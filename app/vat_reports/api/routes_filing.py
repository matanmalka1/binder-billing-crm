"""Routes: advisor review and filing (advisor-only)."""

from fastapi import APIRouter, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession
from app.users.models.user import UserRole
from app.vat_reports.schemas import (
    FileVatReturnRequest,
    VatWorkItemResponse,
)
from app.vat_reports.services.vat_report_service import VatReportService

router = APIRouter(prefix="/vat", tags=["vat-reports"])


@router.post(
    "/work-items/{item_id}/file",
    response_model=VatWorkItemResponse,
)
def file_vat_return(
    item_id: int,
    request: FileVatReturnRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Confirm and file the VAT return.  Locks the period.

    Advisor only.
    Override amount requires written justification.
    """
    if current_user.role != UserRole.ADVISOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="רק יועצים יכולים להגיש דוח מע\"מ",
        )

    service = VatReportService(db)
    item = service.file_vat_return(
        item_id=item_id,
        filed_by=current_user.id,
        submission_method=request.submission_method,
        override_amount=float(request.override_amount) if request.override_amount is not None else None,
        override_justification=request.override_justification,
        submission_reference=request.submission_reference,
        is_amendment=request.is_amendment,
        amends_item_id=request.amends_item_id,
    )
    return item
