from pydantic import BaseModel, Field

from app.dashboard.schemas.dashboard_extended import AttentionResponse, VatDashboardStats


class DashboardSummaryResponse(BaseModel):
    total_clients: int
    active_clients: int
    binders_in_office: int
    binders_ready_for_pickup: int
    open_reminders: int = 0
    vat_stats: VatDashboardStats
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
