from pydantic import BaseModel


class DashboardOverviewResponse(BaseModel):
    """Sprint 2 dashboard overview for management."""
    
    total_clients: int
    active_binders: int
    overdue_binders: int
    binders_due_today: int
    binders_due_this_week: int