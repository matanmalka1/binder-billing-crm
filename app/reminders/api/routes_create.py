from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.reminders.schemas.reminders import ReminderCreateRequest, ReminderResponse
from app.reminders.services.reminder_service import ReminderService

create_router = APIRouter()


@create_router.post(
    "/",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_reminder(
    request: ReminderCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = ReminderService(db)
    reminder = service.create_from_request(request, created_by=user.id)

    resp = ReminderResponse.model_validate(reminder)
    resp.client_record_id = reminder.client_record_id
    return resp
