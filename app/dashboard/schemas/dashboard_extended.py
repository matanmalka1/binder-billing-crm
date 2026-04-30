from datetime import date
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
    category: Optional[str] = None  # "binders" | "vat" | "annual_reports"
    due_label: Optional[str] = None
    description: Optional[str] = None
    urgency: Optional[Literal["overdue", "upcoming"]] = None
    due_date: Optional[date] = None


class BaseAttentionItem(BaseModel):
    item_type: str
    binder_id: Optional[int] = None
    client_id: Optional[int] = None
    business_id: Optional[int] = None
    client_name: Optional[str] = None
    description: str


class UnpaidChargeAttentionItem(BaseAttentionItem):
    item_type: Literal["unpaid_charge"]
    business_name: str
    charge_subject: str
    charge_date: Optional[date] = None
    charge_amount: str
    charge_invoice_number: str
    charge_period: Optional[str] = None


class UnpaidChargesAttentionItem(BaseAttentionItem):
    item_type: Literal["unpaid_charges"]


class ReadyForPickupAttentionItem(BaseAttentionItem):
    item_type: Literal["ready_for_pickup"]


AttentionItem = (
    UnpaidChargeAttentionItem
    | UnpaidChargesAttentionItem
    | ReadyForPickupAttentionItem
)


class AttentionResponse(BaseModel):
    items: list[AttentionItem] = Field(default_factory=list)
    total: int = 0


class AdvisorTodayItem(BaseModel):
    id: int
    label: str
    sublabel: Optional[str] = None
    description: Optional[str] = None
    href: Optional[str] = None


class AdvisorTodayResponse(BaseModel):
    deadline_items: list[AdvisorTodayItem] = Field(default_factory=list)
    reminder_items: list[AdvisorTodayItem] = Field(default_factory=list)


class VatDashboardPeriodStat(BaseModel):
    period: str
    period_label: str
    status_label: str = ""
    submitted: int = 0
    required: int = 0
    pending: int = 0
    completion_percent: int = 0


class VatDashboardStats(BaseModel):
    monthly: VatDashboardPeriodStat
    bimonthly: VatDashboardPeriodStat


class AttentionEmptyCheck(BaseModel):
    key: str
    label: str


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
    advisor_today: AdvisorTodayResponse = Field(default_factory=AdvisorTodayResponse)
    attention_empty_checks: list[AttentionEmptyCheck] = Field(default_factory=list)
