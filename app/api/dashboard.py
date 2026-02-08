from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas import DashboardSummaryResponse
from app.services import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: DBSession, user: CurrentUser):
    """Get dashboard summary counters."""
    service = DashboardService(db)
    summary = service.get_summary()
    return DashboardSummaryResponse(**summary)