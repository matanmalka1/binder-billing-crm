"""Notification center HTTP endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.services.notification_service import NotificationService
from app.notification.schemas.notification_schemas import (
    ManualSendRequest,
    ManualSendResponse,
    NotificationListResponse,
    NotificationSummaryResponse,
)


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

advisor_router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
    status: Optional[NotificationStatus] = None,
    trigger: Optional[NotificationTrigger] = None,
    channel: Optional[NotificationChannel] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    svc = NotificationService(db)
    items, total = svc.list_paginated(
        page=page,
        page_size=page_size,
        client_record_id=client_record_id,
        business_id=business_id,
        status=status,
        trigger=trigger,
        channel=channel,
    )
    return NotificationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=NotificationSummaryResponse)
def get_notification_summary(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
):
    svc = NotificationService(db)
    return svc.get_summary(client_record_id=client_record_id, business_id=business_id)


@advisor_router.post("/send", response_model=ManualSendResponse)
def send_manual_notification(body: ManualSendRequest, db: DBSession, user: CurrentUser):
    svc = NotificationService(db)
    ok = svc.send_manual(body, triggered_by=user.id)
    return ManualSendResponse(ok=ok)
