from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime
from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)


# ── Request schemas ───────────────────────────────────────────────────────────

class NotificationPreviewRequest(BaseModel):
    client_record_id: int = Field(gt=0)
    trigger: NotificationTrigger
    entity_id: int | None = Field(None, gt=0)
    business_id: int | None = Field(None, gt=0)
    confirm_recent_duplicate: bool = False


class NotificationSendRequest(BaseModel):
    client_record_id: int = Field(gt=0)
    trigger: NotificationTrigger
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    entity_id: int | None = Field(None, gt=0)
    business_id: int | None = Field(None, gt=0)
    idempotency_key: str | None = Field(None, max_length=128)
    confirm_recent_duplicate: bool = False


# ── Result schemas ────────────────────────────────────────────────────────────

class NotificationResult(BaseModel):
    status: Literal["sent", "failed", "skipped", "blocked"]
    notification_id: int | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


class NotificationPreviewResponse(BaseModel):
    can_send: bool
    status: Literal["ready", "blocked"]
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    recipient: str | None = None
    subject: str | None = None
    body: str | None = None


# ── Read schemas ──────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    client_record_id: int
    client_name: str | None = None
    business_id: int | None = None
    business_name: str | None = None
    binder_id: int | None = None
    annual_report_id: int | None = None
    signature_request_id: int | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    trigger: NotificationTrigger
    trigger_label: str = ""
    domain_label: str = ""
    channel: NotificationChannel
    recipient: str | None = None
    content_snapshot: str
    subject_snapshot: str | None = None
    status: NotificationStatus
    sent_at: ApiDateTime | None = None
    failed_at: ApiDateTime | None = None
    error_message: str | None = None
    retry_count: int
    triggered_by: int | None = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class NotificationSummaryResponse(BaseModel):
    pending: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


# ── Bulk result ───────────────────────────────────────────────────────────────

class BulkNotificationResultItem(BaseModel):
    entity_id: int | None = None
    client_record_id: int | None = None
    status: Literal["sent", "failed", "skipped", "blocked"]
    notification_id: int | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BulkNotificationResult(BaseModel):
    total: int
    sent: int
    failed: int
    skipped: int
    blocked: int
    results: list[BulkNotificationResultItem] = Field(default_factory=list)
