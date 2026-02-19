from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession
from app.reminders.schemas.reminders import ReminderResponse
from app.reminders.services import ReminderService

mark_sent_router = APIRouter()


@mark_sent_router.post("/{reminder_id}/mark-sent", response_model=ReminderResponse)
def mark_reminder_sent(
    reminder_id: int,
    db: DBSession,
    _user: CurrentUser,
):
    service = ReminderService(db)

    try:
        reminder = service.mark_sent(reminder_id)
        return ReminderResponse.model_validate(reminder)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
