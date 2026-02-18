from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.schemas.dashboard_extended import DashboardOverviewResponse
from app.dashboard.services.dashboard_overview_service import DashboardOverviewService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-overview"],
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(db: DBSession, user: CurrentUser):
    """
    Get dashboard overview (ADMIN only).

    Returns management-level metrics:
    - Total clients
    - Active binders
    - Overdue binders
    - Binders due today
    - Binders due this week
    """
    service = DashboardOverviewService(db)
    overview = service.get_overview(user_role=user.role)
    return DashboardOverviewResponse(**overview)
