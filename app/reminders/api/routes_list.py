from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.reminders.schemas.reminders import ReminderListResponse, ReminderResponse
from app.reminders.services.reminder_service import ReminderService

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
    business_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
):
    service = ReminderService(db)

    if business_id is not None:
        items, total, name_map = service.get_reminders_by_business(
            business_id=business_id, page=page, page_size=page_size
        )
    elif client_id is not None:
        items, total, name_map = service.get_reminders_by_client(
            client_id=client_id, page=page, page_size=page_size
        )
    else:
        items, total, name_map = service.get_reminders(status=status_filter, page=page, page_size=page_size)

    def _to_response(r) -> ReminderResponse:
        resp = ReminderResponse.model_validate(r)
        business_context = name_map.get(r.business_id) if r.business_id is not None else None
        if business_context:
            resp.business_name = business_context["business_name"]
            resp.client_id = business_context["client_id"]
            resp.client_name = business_context["client_name"]
        elif r.client_id is not None:
            resp.client_id = r.client_id
        return resp

    return ReminderListResponse(
        items=[_to_response(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )
