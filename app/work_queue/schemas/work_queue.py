from __future__ import annotations

from datetime import date
from enum import Enum as PyEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.common.source_types import WorkQueueSourceType


class WorkQueueUrgency(str, PyEnum):
    OVERDUE = "overdue"
    APPROACHING = "approaching"
    IMPORTANT = "important"
    UPCOMING = "upcoming"


class WorkQueueLinkedFilter(str, PyEnum):
    LINKED = "linked"
    UNLINKED = "unlinked"


class WorkQueueScope(str, PyEnum):
    SYSTEM = "system"
    MANUAL = "manual"


class WorkQueueSourceSummary(BaseModel):
    source_type: str
    source_id: int
    label: str
    route: Optional[str] = None


class LinkedTaskSummary(BaseModel):
    id: int
    title: str
    status: str
    due_date: Optional[date] = None
    priority: Optional[str] = None
    assigned_user_id: Optional[int] = None
    assigned_role: Optional[str] = None


class WorkQueueWarning(BaseModel):
    key: str
    label: str
    severity: Literal["info", "warning", "danger"] = "warning"


class WorkQueueAction(BaseModel):
    key: str
    label: str
    type: Literal["link", "mutation", "modal"]
    route: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[Literal["get", "post", "patch", "put", "delete"]] = None
    task_id: Optional[int] = None
    payload_schema: Literal["none", "simple", "requires_input"] = "none"
    confirm: bool = False
    confirm_title: Optional[str] = None
    confirm_message: Optional[str] = None
    variant: Literal["primary", "secondary", "danger"] = "secondary"
    disabled: bool = False
    disabled_reason: Optional[str] = None


class WorkQueueItem(BaseModel):
    id: str
    source_type: WorkQueueSourceType
    source_id: int
    title: str
    description: Optional[str] = None
    type_label: Optional[str] = None
    status_label: Optional[str] = None
    due_date: Optional[date] = None
    urgency: WorkQueueUrgency
    client_record_id: Optional[int] = None
    client_name: Optional[str] = None
    office_client_number: Optional[int] = None
    business_id: Optional[int] = None
    source_summary: Optional[WorkQueueSourceSummary] = None
    linked_tasks: list[LinkedTaskSummary] = Field(default_factory=list)
    linked_tasks_count: int = 0
    warnings: list[WorkQueueWarning] = Field(default_factory=list)
    available_actions: list[WorkQueueAction] = Field(default_factory=list)
    metadata: Optional[dict] = None


class WorkQueueSummary(BaseModel):
    total: int
    manual_tasks: int
    linked: int
    unlinked: int
    overdue: int
    approaching: int
    important: int
    upcoming: int
    by_source_type: dict[WorkQueueSourceType, int]
    by_task_status: dict[str, int]


class WorkQueueListResponse(BaseModel):
    items: list[WorkQueueItem]
    total: int
