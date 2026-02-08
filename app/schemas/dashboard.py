from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    binders_in_office: int
    binders_ready_for_pickup: int
    binders_overdue: int