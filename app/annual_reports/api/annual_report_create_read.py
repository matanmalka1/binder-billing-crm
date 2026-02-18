from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import (
    AnnualReportCreateRequest,
    AnnualReportDetailResponse,
    AnnualReportListResponse,
    AnnualReportResponse,
    ScheduleEntryResponse,
    StatusHistoryResponse,
)
from app.annual_reports.services import AnnualReportService


router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _build_detail(report, service: AnnualReportService) -> AnnualReportDetailResponse:
    schedules = service.get_schedules(report.id)
    history = service.get_status_history(report.id)
    response = AnnualReportDetailResponse.model_validate(report)
    response.schedules = [ScheduleEntryResponse.model_validate(s) for s in schedules]
    response.status_history = [StatusHistoryResponse.model_validate(h) for h in history]
    return response


@router.post("", response_model=AnnualReportDetailResponse, status_code=status.HTTP_201_CREATED)
def create_annual_report(body: AnnualReportCreateRequest, db: DBSession, user: CurrentUser):
    """Create a new annual income tax report for a client."""
    service = AnnualReportService(db)
    try:
        report = service.create_report(
            client_id=body.client_id,
            tax_year=body.tax_year,
            client_type=body.client_type,
            created_by=user.id,
            created_by_name=user.full_name,
            deadline_type=body.deadline_type,
            assigned_to=body.assigned_to,
            notes=body.notes,
            has_rental_income=body.has_rental_income,
            has_capital_gains=body.has_capital_gains,
            has_foreign_income=body.has_foreign_income,
            has_depreciation=body.has_depreciation,
            has_exempt_rental=body.has_exempt_rental,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _build_detail(report, service)


@router.get("", response_model=AnnualReportListResponse)
def list_annual_reports(
    db: DBSession,
    user: CurrentUser,
    tax_year: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    """List annual reports (optionally filter by tax_year)."""
    service = AnnualReportService(db)
    items, total = service.list_reports(tax_year=tax_year, page=page, page_size=page_size)
    return AnnualReportListResponse(
        items=[AnnualReportResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/kanban/view", response_model=dict)
def get_kanban_view(db: DBSession, user: CurrentUser):
    """Kanban board view grouped by stage."""
    service = AnnualReportService(db)
    stages = service.kanban_view()
    return {"stages": stages}


@router.get("/overdue", response_model=list[AnnualReportResponse])
def list_overdue(db: DBSession, user: CurrentUser, tax_year: int | None = Query(None)):
    """Reports past their filing deadline that have not been submitted."""
    service = AnnualReportService(db)
    reports = service.get_overdue(tax_year=tax_year)
    return [AnnualReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=AnnualReportDetailResponse)
def get_annual_report(report_id: int, db: DBSession, user: CurrentUser):
    """Get a single report with its schedule entries and status history."""
    service = AnnualReportService(db)
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _build_detail(report, service)
