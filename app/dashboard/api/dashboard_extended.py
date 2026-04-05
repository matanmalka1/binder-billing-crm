from fastapi import APIRouter, Depends

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.dashboard.schemas.dashboard_extended import (
    AttentionResponse,
)
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-extended"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

@router.get("/attention", response_model=AttentionResponse)
def get_attention_items(
    db: DBSession,
    user: CurrentUser,
):
    """Get items requiring attention."""
    service = DashboardExtendedService(db)
    items = service.get_attention_items(user_role=user.role)

    return AttentionResponse(
        items=items,
        total=len(items),
    )
