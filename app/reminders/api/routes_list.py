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
        items, total, context_map = service.get_reminders_by_business(
            business_id=business_id, page=page, page_size=page_size
        )
    elif client_id is not None:
        items, total, context_map = service.get_reminders_by_client(
            client_id=client_id, page=page, page_size=page_size
        )
    else:
        items, total, context_map = service.get_reminders(status=status_filter, page=page, page_size=page_size)

    def _to_response(r) -> ReminderResponse:
        resp = ReminderResponse.model_validate(r)
        ctx = context_map.get(r.id)
        if ctx:
            # client_id and client_name are always present (client_id is never null)
            resp.client_id = ctx["client_id"]
            resp.client_name = ctx["client_name"]
            resp.client_id_number = ctx["client_id_number"]
            # business context is present only when the reminder is business-scoped
            resp.business_id = ctx["business_id"]
            resp.business_name = ctx["business_name"]
        return resp

    return ReminderListResponse(
        items=[_to_response(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )