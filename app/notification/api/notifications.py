"""Notification center HTTP endpoints (8.3 + 8.6)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.notification.repositories.notification_repository import NotificationRepository
from pydantic import BaseModel


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    client_id: int
    trigger: str
    channel: str
    status: str
    severity: str
    content_snapshot: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    notification_ids: list[int]


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    updated: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: DBSession,
    user: CurrentUser,
    client_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Return recent notifications ordered by created_at desc."""
    repo = NotificationRepository(db)
    items = repo.list_recent(limit=limit, client_id=client_id)
    return [NotificationResponse.model_validate(n) for n in items]


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: DBSession,
    user: CurrentUser,
    client_id: Optional[int] = None,
):
    """Return count of unread notifications."""
    repo = NotificationRepository(db)
    return UnreadCountResponse(unread_count=repo.count_unread(client_id=client_id))


@router.post("/mark-read", response_model=MarkReadResponse)
def mark_read(body: MarkReadRequest, db: DBSession, user: CurrentUser):
    """Mark specific notifications as read."""
    repo = NotificationRepository(db)
    updated = repo.mark_read(body.notification_ids)
    return MarkReadResponse(updated=updated)


@router.post("/mark-all-read", response_model=MarkReadResponse)
def mark_all_read(
    db: DBSession,
    user: CurrentUser,
    client_id: int = Query(...),
):
    """Mark all unread notifications for a client as read."""
    repo = NotificationRepository(db)
    updated = repo.mark_all_read(client_id)
    return MarkReadResponse(updated=updated)
