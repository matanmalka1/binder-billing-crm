from fastapi import APIRouter, Depends

from app.binders.services.binder_handover_reminder_service import BinderHandoverReminderService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(
    prefix="/binders",
    tags=["binders-reminders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.post("/{binder_id}/handover-reminder", status_code=204)
def send_handover_reminder(binder_id: int, db: DBSession, user: CurrentUser):
    BinderHandoverReminderService(db).send_handover_reminder(binder_id, triggered_by=user.id)
