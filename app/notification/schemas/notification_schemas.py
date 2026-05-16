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
    client_record_id: int
    client_name: Optional[str] = None  # enriched by service layer
    business_id: Optional[int] = None
    business_name: Optional[str] = None  # enriched by service layer
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
    triggered_by: Optional[int] = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class NotificationSummaryResponse(BaseModel):
    pending: int
    sent: int
    failed: int
    total: int


class ManualSendRequest(BaseModel):
    client_record_id: int = Field(gt=0)
    business_id: Optional[int] = Field(None, gt=0)
    preferred_channel: NotificationChannel = NotificationChannel.EMAIL
    message: str = Field(min_length=1, max_length=1000)


class ManualSendResponse(BaseModel):
    ok: bool


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
