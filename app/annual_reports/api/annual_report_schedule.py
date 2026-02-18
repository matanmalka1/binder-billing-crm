from fastapi import APIRouter, Depends, HTTPException

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.schemas import (  
    ScheduleAddRequest,
    ScheduleCompleteRequest,
    ScheduleEntryResponse,
)
from app.annual_reports.services import AnnualReportService


router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{report_id}/schedules", response_model=list[ScheduleEntryResponse])
def get_schedules(report_id: int, db: DBSession, user: CurrentUser):
    """Return all schedule entries for a report."""
    service = AnnualReportService(db)
    try:
        return [ScheduleEntryResponse.model_validate(s) for s in service.get_schedules(report_id)]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{report_id}/schedules", response_model=ScheduleEntryResponse, status_code=201)
def add_schedule(report_id: int, body: ScheduleAddRequest, db: DBSession, user: CurrentUser):
    """Manually add a schedule to a report (auto-generated ones are created at report creation)."""
    service = AnnualReportService(db)
    try:
        entry = service.add_schedule(report_id, body.schedule, notes=body.notes)
        return ScheduleEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{report_id}/schedules/complete", response_model=ScheduleEntryResponse)
def complete_schedule(report_id: int, body: ScheduleCompleteRequest, db: DBSession, user: CurrentUser):
    """Mark a specific schedule as complete."""
    service = AnnualReportService(db)
    try:
        entry = service.complete_schedule(report_id, body.schedule)
        return ScheduleEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))