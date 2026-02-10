from datetime import date
from pydantic import BaseModel
from typing import Optional

class DashboardOverviewResponse(BaseModel):
    """Sprint 2 dashboard overview for management."""
    
    total_clients: int
    active_binders: int
    overdue_binders: int
    binders_due_today: int
    binders_due_this_week: int

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
    client_id: int
    client_name: str
    description: str


class AttentionResponse(BaseModel):
    items: list[AttentionItem]
    total: int