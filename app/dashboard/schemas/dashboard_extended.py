from typing import Any, Optional

from pydantic import BaseModel, Field


class ConfirmDetails(BaseModel):
    title: str
    message: str
    confirm_label: str
    cancel_label: str


class DashboardQuickAction(BaseModel):
    id: str
    key: str
    label: str
    method: str
    endpoint: str
    payload: Optional[dict[str, Any]] = None
    confirm: Optional[ConfirmDetails] = None
    client_name: Optional[str] = None
    binder_number: Optional[str] = None


class AttentionItem(BaseModel):
    item_type: str
    binder_id: Optional[int] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    description: str


class AttentionResponse(BaseModel):
    items: list[AttentionItem] = Field(default_factory=list)
    total: int = 0


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview for management."""

    total_clients: int
    active_binders: int
    work_state: Optional[str] = None
    signals: Optional[list[str]] = None
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)
    attention: AttentionResponse = Field(default_factory=AttentionResponse)


class WorkQueueItem(BaseModel):
    binder_id: int
    client_id: int
    client_name: str
    binder_number: str
    work_state: str
    signals: list[str]
    days_since_received: int


class WorkQueueResponse(BaseModel):
    items: list[WorkQueueItem]
    page: int
    page_size: int
    total: int
