from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas.annual_report_detail import (
    AnnualReportDetailUpdateRequest,
    ReportDetailResponse,
)
from app.annual_reports.services import AnnualReportDetailService

router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-report-detail"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _verify_report_exists(report_id: int, db) -> None:
    from app.annual_reports.repositories import AnnualReportRepository
    report = AnnualReportRepository(db).get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Annual report not found"
        )


@router.get("/{report_id}/details", response_model=ReportDetailResponse)
def get_annual_report_detail(report_id: int, db: DBSession, user: CurrentUser):
    _verify_report_exists(report_id, db)
    service = AnnualReportDetailService(db)
    detail = service.get_detail(report_id)
    if detail is None:
        return ReportDetailResponse(report_id=report_id)
    return ReportDetailResponse.model_validate(detail)


@router.patch("/{report_id}/details", response_model=ReportDetailResponse)
def update_annual_report_detail(
    report_id: int,
    request: AnnualReportDetailUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    _verify_report_exists(report_id, db)
    service = AnnualReportDetailService(db)
    try:
        update_data = request.model_dump(exclude_unset=True)
        detail = service.update_detail(report_id, **update_data)
        return ReportDetailResponse.model_validate(detail)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))