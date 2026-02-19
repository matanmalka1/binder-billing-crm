from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession
from app.reminders.schemas.reminders import ReminderListResponse, ReminderResponse
from app.reminders.services import ReminderService

list_router = APIRouter()


@list_router.get("/", response_model=ReminderListResponse)
def list_reminders(
    db: DBSession,
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    service = ReminderService(db)

    try:
        items, total = service.get_reminders(status=status_filter, page=page, page_size=page_size)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )
