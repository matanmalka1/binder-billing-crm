from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.dashboard.schemas.dashboard import DashboardSummaryResponse
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: DBSession, user: CurrentUser):
    """Get dashboard summary counters."""
    service = DashboardService(db)
    summary = service.get_summary(user_role=user.role)
    return DashboardSummaryResponse(**summary)
