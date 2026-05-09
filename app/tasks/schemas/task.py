from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.api_types import ApiDateTime, PaginatedResponse
from app.tasks.models.task import TaskPriority, TaskStatus


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    due_date: Optional[ApiDateTime] = None
    assigned_to_user_id: Optional[int] = Field(None, gt=0)
    assigned_role: Optional[str] = Field(None, max_length=50)
    source_domain: Optional[str] = Field(None, max_length=100)
    source_id: Optional[int] = Field(None, gt=0)
    action_key: Optional[str] = Field(None, max_length=100)
    action_payload: Optional[dict[str, Any]] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[ApiDateTime] = None
    assigned_to_user_id: Optional[int] = Field(None, gt=0)
    assigned_role: Optional[str] = Field(None, max_length=50)
    action_key: Optional[str] = Field(None, max_length=100)
    action_payload: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[ApiDateTime] = None
    assigned_to_user_id: Optional[int] = None
    assigned_role: Optional[str] = None
    source_domain: Optional[str] = None
    source_id: Optional[int] = None
    action_key: Optional[str] = None
    action_payload: Optional[dict[str, Any]] = None
    created_by_user_id: Optional[int] = None
    completed_by_user_id: Optional[int] = None
    completed_at: Optional[ApiDateTime] = None
    canceled_at: Optional[ApiDateTime] = None
    created_at: ApiDateTime
    updated_at: ApiDateTime

    model_config = {"from_attributes": True}


TaskListResponse = PaginatedResponse[TaskResponse]
