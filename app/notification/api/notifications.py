"""Notification center HTTP endpoints."""

import datetime

from fastapi import APIRouter, Depends, Query

from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.schemas.notification_schemas import (
    NotificationListResponse,
    NotificationPreviewRequest,
    NotificationPreviewResponse,
    NotificationResult,
    NotificationSendRequest,
    NotificationSummaryResponse,
)
from app.core.exceptions import AppError
from app.notification.services.notification_service import NotificationService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

_ALLOWED_PAGE_SIZES = {25, 50}

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: DBSession,
    client_record_id: int | None = None,
    business_id: int | None = None,
    status: NotificationStatus | None = None,
    trigger: NotificationTrigger | None = None,
    channel: NotificationChannel | None = None,
    triggered_by: int | None = None,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=50),
):
    if page_size not in _ALLOWED_PAGE_SIZES:
        raise AppError(
            f"page_size חייב להיות אחד מהערכים: {sorted(_ALLOWED_PAGE_SIZES)}",
            "NOTIFICATION.INVALID_PAGE_SIZE",
            status_code=422,
        )
    svc = NotificationService(db)
    items, total = svc.list_paginated(
        page=page,
        page_size=page_size,
        client_record_id=client_record_id,
        business_id=business_id,
        status=status,
        trigger=trigger,
        channel=channel,
        triggered_by=triggered_by,
        date_from=date_from,
        date_to=date_to,
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
    client_record_id: int | None = None,
    business_id: int | None = None,
):
    svc = NotificationService(db)
    return svc.get_summary(client_record_id=client_record_id, business_id=business_id)


@router.post("/preview", response_model=NotificationPreviewResponse)
def preview_notification(
    body: NotificationPreviewRequest,
    db: DBSession,
    user: CurrentUser,
):
    svc = NotificationService(db)
    return svc.preview(body, triggered_by=user.id)


@router.post("/send", response_model=NotificationResult)
def send_notification(
    body: NotificationSendRequest,
    db: DBSession,
    user: CurrentUser,
):
    svc = NotificationService(db)
    return svc.send(body, triggered_by=user.id)
