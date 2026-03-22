from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

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
    business_id: Optional[int] = Query(None),
):
    service = ReminderService(db)

    if business_id is not None:
        items, total, name_map = service.get_reminders_by_business(
            business_id=business_id, page=page, page_size=page_size
        )
    else:
        items, total, name_map = service.get_reminders(status=status_filter, page=page, page_size=page_size)

    def _to_response(r) -> ReminderResponse:
        resp = ReminderResponse.model_validate(r)
        resp.business_name = name_map.get(r.business_id)
        return resp

    return ReminderListResponse(
        items=[_to_response(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )
