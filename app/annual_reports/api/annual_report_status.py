from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import (  # FIXED: was app.schemas.annual_report
    AnnualReportResponse,
    StatusHistoryResponse,
    StatusTransitionRequest,
    DeadlineUpdateRequest,
)
from app.annual_reports.services import AnnualReportService


router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("/{report_id}/status", response_model=AnnualReportResponse)
def transition_status(
    report_id: int,
    body: StatusTransitionRequest,
    db: DBSession,
    user: CurrentUser,
):
    """
    Move the report to a new status.

    Only valid transitions are accepted (e.g. COLLECTING_DOCS → DOCS_COMPLETE).
    Attempting an invalid jump returns 400.
    """
    service = AnnualReportService(db)
    try:
        report = service.transition_status(
            report_id=report_id,
            new_status=body.status,
            changed_by=user.id,
            changed_by_name=user.full_name,
            note=body.note,
            ita_reference=body.ita_reference,
            assessment_amount=float(body.assessment_amount) if body.assessment_amount else None,
            refund_due=float(body.refund_due) if body.refund_due else None,
            tax_due=float(body.tax_due) if body.tax_due else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AnnualReportResponse.model_validate(report)


@router.post("/{report_id}/deadline", response_model=AnnualReportResponse)
def update_deadline(
    report_id: int,
    body: DeadlineUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """
    Update the deadline type for a report.

    Switching to 'extended' moves the deadline to January 31 of the year
    after next — used for authorised electronic representatives (מייצגים).
    """
    service = AnnualReportService(db)
    try:
        report = service.update_deadline(
            report_id=report_id,
            deadline_type=body.deadline_type,
            changed_by=user.id,
            changed_by_name=user.full_name,
            custom_deadline_note=body.custom_deadline_note,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return AnnualReportResponse.model_validate(report)


@router.get("/{report_id}/history", response_model=list[StatusHistoryResponse])
def get_history(report_id: int, db: DBSession, user: CurrentUser):
    """Full status history for a report."""
    service = AnnualReportService(db)
    try:
        return [StatusHistoryResponse.model_validate(h) for h in service.get_status_history(report_id)]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))