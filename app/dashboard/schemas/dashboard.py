from pydantic import BaseModel, Field

from app.dashboard.schemas.dashboard_extended import AttentionResponse


class DashboardSummaryResponse(BaseModel):
    binders_in_office: int
    binders_ready_for_pickup: int
    attention: AttentionResponse = Field(default_factory=AttentionResponse)
