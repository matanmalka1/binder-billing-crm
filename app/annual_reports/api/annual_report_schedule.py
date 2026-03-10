from fastapi import APIRouter, Depends

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


@router.post("/{report_id}/schedules", response_model=ScheduleEntryResponse, status_code=201)
def add_schedule(report_id: int, body: ScheduleAddRequest, db: DBSession, user: CurrentUser):
    """Manually add a schedule to a report (auto-generated ones are created at report creation)."""
    service = AnnualReportService(db)
    entry = service.add_schedule(report_id, body.schedule, notes=body.notes)
    return ScheduleEntryResponse.model_validate(entry)


@router.get("/{report_id}/schedules", response_model=list[ScheduleEntryResponse])
def list_schedules(report_id: int, db: DBSession, user: CurrentUser):
    """List all schedules for a specific annual report."""
    service = AnnualReportService(db)
    schedules = service.get_schedules(report_id)
    return [ScheduleEntryResponse.model_validate(entry) for entry in schedules]


@router.post("/{report_id}/schedules/complete", response_model=ScheduleEntryResponse)
def complete_schedule(report_id: int, body: ScheduleCompleteRequest, db: DBSession, user: CurrentUser):
    """Mark a specific schedule as complete."""
    service = AnnualReportService(db)
    entry = service.complete_schedule(report_id, body.schedule)
    return ScheduleEntryResponse.model_validate(entry)
