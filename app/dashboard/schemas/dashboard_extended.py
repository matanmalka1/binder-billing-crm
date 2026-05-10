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


class AttentionBoardItem(BaseModel):
    id: str
    source_type: str
    source_id: int
    title: str
    client_name: Optional[str] = None
    due_date: Optional[date] = None
    days_delta: int = 0
    reason: Optional[str] = None
    amount: Optional[str] = None
    urgency: str
    href: str


class AttentionResponse(BaseModel):
    items: list[AttentionBoardItem] = Field(default_factory=list)
    total: int = 0


class AdvisorTodayItem(BaseModel):
    id: int
    label: str
    sublabel: Optional[str] = None
    description: Optional[str] = None
    href: Optional[str] = None


class AdvisorTodayResponse(BaseModel):
    deadline_items: list[AdvisorTodayItem] = Field(default_factory=list)


class VatDashboardPeriodStat(BaseModel):
    period: str
    period_label: str
    status_label: str = ""
    submitted: int = 0
    required: int = 0
    pending: int = 0
    completion_percent: int = 0


class AdvancePaymentDashboardStats(BaseModel):
    monthly: VatDashboardPeriodStat
    bimonthly: VatDashboardPeriodStat


class VatDashboardStats(BaseModel):
    monthly: VatDashboardPeriodStat
    bimonthly: VatDashboardPeriodStat
    advance_payments: AdvancePaymentDashboardStats


class RecentActivityItem(BaseModel):
    id: int
    date: str
    time: str
    label: str
    client_name: str
    href: str
    activity_type: str


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview — advisor gets full data, secretary gets operational subset."""

    is_empty: bool
    open_charges_count: int = 0
    open_charges_amount_ils: Optional[str] = None
    vat_stats: VatDashboardStats
    quick_actions: list[DashboardQuickAction] = Field(default_factory=list)
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
    advisor_today: AdvisorTodayResponse = Field(default_factory=AdvisorTodayResponse)
    recent_activity: list[RecentActivityItem] = Field(default_factory=list)
