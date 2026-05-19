from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.reminders.schemas.reminders import ReminderListResponse
from app.reminders.services.reminder_service import ReminderService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

list_router = APIRouter()


@list_router.get(
    "/",
    response_model=ReminderListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_reminders(
    db: DBSession,
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    service = ReminderService(db)
    items, total = service.get_reminders(
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return ReminderListResponse(
        items=service.to_responses(items),
        page=page,
        page_size=page_size,
        total=total,
    )
