
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
    client_name: str | None = None  # enriched by service layer
    business_id: int | None = None
    business_name: str | None = None  # enriched by service layer
    binder_id: int | None = None
    trigger: NotificationTrigger
    channel: NotificationChannel
    severity: NotificationSeverity
    recipient: str
    content_snapshot: str
    status: NotificationStatus
    sent_at: ApiDateTime | None = None
    failed_at: ApiDateTime | None = None
    error_message: str | None = None
    retry_count: int
    triggered_by: int | None = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class NotificationSummaryResponse(BaseModel):
    pending: int
    sent: int
    failed: int
    total: int


class ManualSendRequest(BaseModel):
    client_record_id: int = Field(gt=0)
    business_id: int | None = Field(None, gt=0)
    preferred_channel: NotificationChannel = NotificationChannel.EMAIL
    message: str = Field(min_length=1, max_length=1000)


class ManualSendResponse(BaseModel):
    ok: bool


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
