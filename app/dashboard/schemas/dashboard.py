from pydantic import BaseModel, Field

from app.dashboard.schemas.dashboard_extended import AttentionResponse


class DashboardSummaryResponse(BaseModel):
    binders_in_office: int
    binders_ready_for_pickup: int
    open_reminders: int = 0
    vat_due_this_month: int = 0
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
