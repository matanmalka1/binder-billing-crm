from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession
from app.reminders.schemas.reminders import ReminderResponse
from app.reminders.services.reminder_context import DEADLINE_TYPE_LABELS
from app.reminders.services.reminder_service import ReminderService

get_router = APIRouter()


@get_router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    db: DBSession,
    _user: CurrentUser,
):
    service = ReminderService(db)

    reminder = service.get_reminder(reminder_id)

    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="התזכורת לא נמצאה")

    resp = ReminderResponse.model_validate(reminder)
    if reminder.tax_deadline_id:
        deadline = service.tax_deadline_repo.get_by_id(reminder.tax_deadline_id)
        if deadline:
            resp.display_label = DEADLINE_TYPE_LABELS.get(deadline.deadline_type.value, "מועד מס מתקרב")
    return resp
