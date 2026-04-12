from typing import Optional

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)


class NotificationResponse(BaseModel):
    id: int
    client_id: int                          # PRIMARY anchor — always present
    business_id: Optional[int] = None      # OPTIONAL context
    business_name: Optional[str] = None    # enriched by service layer
    binder_id: Optional[int] = None
    trigger: NotificationTrigger
    channel: NotificationChannel
    severity: NotificationSeverity
    recipient: str
    content_snapshot: str
    status: NotificationStatus
    sent_at: Optional[ApiDateTime] = None
    failed_at: Optional[ApiDateTime] = None
    error_message: Optional[str] = None
    retry_count: int
    is_read: bool
    read_at: Optional[ApiDateTime] = None
    triggered_by: Optional[int] = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    notification_ids: list[int] = Field(min_length=1)


class MarkReadResponse(BaseModel):
    updated: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class SendNotificationRequest(BaseModel):
    """Manual send by advisor — scoped to a business."""
    business_id: int
    channel: NotificationChannel
    message: str = Field(min_length=1, max_length=1000)
    severity: NotificationSeverity = NotificationSeverity.INFO


class SendNotificationResponse(BaseModel):
    ok: bool


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int