from pydantic import BaseModel, Field

from app.schemas.dashboard_extended import AttentionResponse


class DashboardSummaryResponse(BaseModel):
    binders_in_office: int
    binders_ready_for_pickup: int
    binders_overdue: int
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
