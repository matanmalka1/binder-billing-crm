from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.reminders.api.deps import advisor_or_secretary
from app.reminders.schemas.reminders import ReminderResponse
from app.reminders.services import ReminderService

get_router = APIRouter()


@get_router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(reminder_id: int, deps = Depends(advisor_or_secretary)):
    db, _user = deps
    service = ReminderService(db)

    reminder = service.get_reminder(reminder_id)

    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    return ReminderResponse.model_validate(reminder)
