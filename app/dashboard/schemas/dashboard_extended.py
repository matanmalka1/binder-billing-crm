from typing import Any, Literal, Optional

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
    category: Optional[str] = None  # "binders" | "vat" | "annual_reports" | "charges" | "clients"
    due_label: Optional[str] = None  # e.g. "פג תוקף לפני 3 ימים"


class AttentionItem(BaseModel):
    item_type: Literal["unpaid_charge", "unpaid_charges", "ready_for_pickup"]
    binder_id: Optional[int] = None
    client_id: Optional[int] = None
    business_id: Optional[int] = None
    client_name: Optional[str] = None
    description: str


class AttentionResponse(BaseModel):
    items: list[AttentionItem] = Field(default_factory=list)
    total: int = 0


class VatDashboardPeriodStat(BaseModel):
    period: str
    period_label: str
    submitted: int = 0
    required: int = 0
    pending: int = 0
    completion_percent: int = 0


class VatDashboardStats(BaseModel):
    monthly: VatDashboardPeriodStat
    bimonthly: VatDashboardPeriodStat


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview for management."""

    total_clients: int
    active_clients: int
    active_binders: int
    binders_in_office: int = 0
    binders_ready_for_pickup: int = 0
    open_reminders: int = 0
    vat_stats: VatDashboardStats
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
