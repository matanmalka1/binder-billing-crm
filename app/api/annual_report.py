from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import ReportStage, UserRole
from app.schemas.annual_report import (
    AnnualReportCreateRequest,
    AnnualReportListResponse,
    AnnualReportResponse,
    AnnualReportSubmitRequest,
    AnnualReportTransitionRequest,
    KanbanResponse,
    KanbanStageResponse,
)
from app.services.annual_report_service import AnnualReportService

router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("", response_model=AnnualReportResponse, status_code=status.HTTP_201_CREATED)
def create_annual_report(
    request: AnnualReportCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new annual report."""
    service = AnnualReportService(db)

    try:
        report = service.create_report(
            client_id=request.client_id,
            tax_year=request.tax_year,
            form_type=request.form_type,
            due_date=request.due_date,
            notes=request.notes,
        )
        return AnnualReportResponse.model_validate(report)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=AnnualReportListResponse)
def list_annual_reports(
    db: DBSession,
    user: CurrentUser,
    client_id: Optional[int] = None,
    tax_year: Optional[int] = None,
    stage: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List annual reports with filters."""
    service = AnnualReportService(db)

    if stage:
        try:
            stage_enum = ReportStage(stage)
            items = service.get_reports_by_stage(stage_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage: {stage}",
            )
    elif client_id:
        items = service.get_client_reports(client_id, tax_year)
    else:
        items = []

    total = len(items)
    offset = (page - 1) * page_size
    paginated = items[offset : offset + page_size]

    return AnnualReportListResponse(
        items=[AnnualReportResponse.model_validate(r) for r in paginated],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{report_id}", response_model=AnnualReportResponse)
def get_annual_report(report_id: int, db: DBSession, user: CurrentUser):
    """Get annual report by ID."""
    service = AnnualReportService(db)
    report = service.report_repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annual report not found",
        )

    return AnnualReportResponse.model_validate(report)


@router.post("/{report_id}/transition", response_model=AnnualReportResponse)
def transition_report_stage(
    report_id: int,
    request: AnnualReportTransitionRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Transition report to new stage."""
    service = AnnualReportService(db)

    try:
        new_stage = ReportStage(request.to_stage)
        report = service.transition_stage(report_id, new_stage)
        return AnnualReportResponse.model_validate(report)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{report_id}/submit",
    response_model=AnnualReportResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def submit_annual_report(
    report_id: int,
    request: AnnualReportSubmitRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Mark report as submitted (ADVISOR only)."""
    service = AnnualReportService(db)

    try:
        report = service.mark_submitted(report_id, request.submitted_at)
        return AnnualReportResponse.model_validate(report)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/kanban/view", response_model=KanbanResponse)
def get_kanban_view(db: DBSession, user: CurrentUser):
    """Get kanban view of all reports."""
    service = AnnualReportService(db)
    from app.repositories.client_repository import ClientRepository

    client_repo = ClientRepository(db)

    stages = []
    for stage in ReportStage:
        reports = service.get_reports_by_stage(stage)
        stage_data = []

        for report in reports:
            client = client_repo.get_by_id(report.client_id)
            days_until_due = (
                (report.due_date - date.today()).days if report.due_date else None
            )

            stage_data.append(
                {
                    "id": report.id,
                    "client_id": report.client_id,
                    "client_name": client.full_name if client else "Unknown",
                    "tax_year": report.tax_year,
                    "days_until_due": days_until_due,
                }
            )

        stages.append(KanbanStageResponse(stage=stage.value, reports=stage_data))

    return KanbanResponse(stages=stages)