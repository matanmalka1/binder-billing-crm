"""Notification center HTTP endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.notification.services.notification_service import NotificationService
from app.notification.models.notification import NotificationTrigger
from app.notification.schemas.notification_schemas import (
    MarkReadRequest,
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    UnreadCountResponse,
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
    client_record_id: Optional[int] = None,      # PRIMARY filter — all notifications for a legal entity
    business_id: Optional[int] = None,    # SECONDARY filter — narrow to one business
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return paginated notifications ordered by created_at desc.

    Use client_record_id to get all notifications for a legal entity.
    Optionally combine with business_id to scope to a specific business.
    """
    svc = NotificationService(db)
    items, total = svc.list_paginated(
        page=page,
        page_size=page_size,
        client_record_id=client_record_id,
        business_id=business_id,
    )
    return NotificationListResponse(
        items=items,   # already NotificationResponse from service enrichment
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
):
    svc = NotificationService(db)
    return UnreadCountResponse(
        unread_count=svc.count_unread(client_record_id=client_record_id, business_id=business_id)
    )


@router.post("/mark-read", response_model=MarkReadResponse)
def mark_read(body: MarkReadRequest, db: DBSession, user: CurrentUser):
    """Mark specific notifications as read."""
    svc = NotificationService(db)
    updated = svc.mark_read(body.notification_ids)
    return MarkReadResponse(updated=updated)


@router.post("/mark-all-read", response_model=MarkReadResponse)
def mark_all_read(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_id: Optional[int] = None,
):
    """Mark all unread notifications as read (optionally scoped to client or business)."""
    svc = NotificationService(db)
    updated = svc.mark_all_read(client_record_id=client_record_id, business_id=business_id)
    return MarkReadResponse(updated=updated)


@advisor_router.post("/send", response_model=SendNotificationResponse)
def send_notification(
    body: SendNotificationRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Send a manual notification to a business (ADVISOR only)."""
    svc = NotificationService(db)
    ok = svc.send_notification(
        business_id=body.business_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content=body.message,
        triggered_by=user.id,
        preferred_channel=body.channel.value,
        severity=body.severity,
    )
    return SendNotificationResponse(ok=ok)
