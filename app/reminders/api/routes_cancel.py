from __future__ import annotations

from fastapi import APIRouter

from app.users.api.deps import CurrentUser, DBSession
from app.reminders.schemas.reminders import ReminderResponse
from app.reminders.services.reminder_service import ReminderService

cancel_router = APIRouter()


@cancel_router.post("/{reminder_id}/cancel", response_model=ReminderResponse)
def cancel_reminder(
    reminder_id: int,
    db: DBSession,
    _user: CurrentUser,
):
    service = ReminderService(db)

    reminder = service.cancel_reminder(reminder_id)
    return ReminderResponse.model_validate(reminder)
