from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime, PaginatedResponse
from app.reminders.models.reminder import ReminderActionType, ReminderStatus


class ReminderCreateRequest(BaseModel):
    fire_at: ApiDateTime
    action_type: ReminderActionType
    source_domain: Optional[str] = Field(None, max_length=100)
    source_id: Optional[int] = Field(None, gt=0)
    target_task_id: Optional[int] = Field(None, gt=0)
    notification_template_key: Optional[str] = Field(None, max_length=100)
    payload: Optional[dict[str, Any]] = None


class ReminderResponse(BaseModel):
    id: int
    fire_at: ApiDateTime
    status: ReminderStatus
    action_type: ReminderActionType
    source_domain: Optional[str] = None
    source_id: Optional[int] = None
    target_task_id: Optional[int] = None
    notification_template_key: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_by_user_id: Optional[int] = None
    fired_at: Optional[ApiDateTime] = None
    failure_reason: Optional[str] = None
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = {"from_attributes": True}


class FireDueResponse(BaseModel):
    processed: int
    fired: int
    failed: int


ReminderListResponse = PaginatedResponse[ReminderResponse]
