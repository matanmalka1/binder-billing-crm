from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.annual_reports.services.annual_report_client_reminder_service import AnnualReportClientReminderService

router = APIRouter(
    prefix="/annual-reports",
    tags=["annual-reports-reminders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.post("/{report_id}/client-reminder", status_code=204)
def send_client_reminder(report_id: int, db: DBSession, user: CurrentUser):
    AnnualReportClientReminderService(db).send_client_reminder(report_id, triggered_by=user.id)
