from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field

class DashboardQuickAction(BaseModel):
    key: str
    label: str
    method: str
    endpoint: str
    payload: Optional[dict[str, Any]] = None
    confirm_required: bool = False
    confirm_title: Optional[str] = None
    confirm_message: Optional[str] = None
    confirm_label: Optional[str] = None
    cancel_label: Optional[str] = None


class DashboardOverviewResponse(BaseModel):
    """Sprint 2 dashboard overview for management."""

    total_clients: int
    active_binders: int
    overdue_binders: int
    binders_due_today: int
    binders_due_this_week: int
    work_state: Optional[str] = None
    sla_state: Optional[str] = None
    signals: Optional[list[str]] = None
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)


class WorkQueueItem(BaseModel):
    binder_id: int
    client_id: int
    client_name: str
    binder_number: str
    work_state: str
    signals: list[str]
    days_since_received: int
    expected_return_at: date


class WorkQueueResponse(BaseModel):
    items: list[WorkQueueItem]
    page: int
    page_size: int
    total: int


class AlertItem(BaseModel):
    binder_id: int
    client_id: int
    client_name: str
    binder_number: str
    alert_type: str
    days_overdue: Optional[int] = None
    days_remaining: Optional[int] = None


class AlertsResponse(BaseModel):
    items: list[AlertItem]
    total: int


class AttentionItem(BaseModel):
    item_type: str
    binder_id: Optional[int] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    description: str


class AttentionResponse(BaseModel):
    items: list[AttentionItem]
    total: int
