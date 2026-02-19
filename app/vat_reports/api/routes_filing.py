"""Routes: advisor review and filing (advisor-only)."""

from fastapi import APIRouter, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession
from app.users.models.user import UserRole
from app.vat_reports.schemas import (
    FileVatReturnRequest,
    VatWorkItemResponse,
)
from app.vat_reports.services.service import VatReportService

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
            detail="Only advisors can file a VAT return",
        )

    service = VatReportService(db)
    try:
        item = service.file_vat_return(
            item_id=item_id,
            filed_by=current_user.id,
            filing_method=request.filing_method,
            override_amount=float(request.override_amount) if request.override_amount is not None else None,
            override_justification=request.override_justification,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item
