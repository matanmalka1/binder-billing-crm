from fastapi import APIRouter

from app.users.api.deps import CurrentUser, DBSession
from app.dashboard.schemas.dashboard import DashboardSummaryResponse
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: DBSession, user: CurrentUser):
    """Get dashboard summary counters."""
    service = DashboardService(db)
    summary = service.get_summary(user_role=user.role)
    return DashboardSummaryResponse(**summary)
