from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.services.binder_pickup_reminder_service import BinderPickupReminderService

router = APIRouter(
    prefix="/binders",
    tags=["binders-reminders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.post("/{binder_id}/pickup-reminder", status_code=204)
def send_pickup_reminder(binder_id: int, db: DBSession, user: CurrentUser):
    BinderPickupReminderService(db).send_pickup_reminder(binder_id, triggered_by=user.id)
