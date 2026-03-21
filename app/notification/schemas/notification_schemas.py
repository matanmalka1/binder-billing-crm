from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)


class NotificationResponse(BaseModel):
    id: int
    business_id: int
    binder_id: Optional[int] = None
    trigger: NotificationTrigger
    channel: NotificationChannel
    severity: NotificationSeverity
    recipient: str
    content_snapshot: str
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int
    is_read: bool
    read_at: Optional[datetime] = None
    triggered_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    notification_ids: list[int] = Field(min_length=1)


class MarkReadResponse(BaseModel):
    updated: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class SendNotificationRequest(BaseModel):
    """שליחה ידנית על ידי יועץ."""
    business_id: int
    channel: NotificationChannel
    message: str = Field(min_length=1, max_length=1000)
    severity: NotificationSeverity = NotificationSeverity.INFO


class SendNotificationResponse(BaseModel):
    ok: bool
