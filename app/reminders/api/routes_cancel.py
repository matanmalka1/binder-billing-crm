from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.reminders.api.deps import advisor_or_secretary
from app.reminders.schemas.reminders import ReminderResponse
from app.reminders.services import ReminderService

cancel_router = APIRouter()


@cancel_router.post("/{reminder_id}/cancel", response_model=ReminderResponse)
def cancel_reminder(reminder_id: int, deps = Depends(advisor_or_secretary)):
    db, _user = deps
    service = ReminderService(db)

    try:
        reminder = service.cancel_reminder(reminder_id)
        return ReminderResponse.model_validate(reminder)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
