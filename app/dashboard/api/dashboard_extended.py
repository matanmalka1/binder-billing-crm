from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.dashboard.schemas.dashboard_extended import (
    AttentionResponse,
    WorkQueueResponse,
)
from app.dashboard.services.dashboard_extended_service import DashboardExtendedService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard-extended"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/work-queue", response_model=WorkQueueResponse)
def get_work_queue(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get operational work queue."""
    service = DashboardExtendedService(db)
    items, total = service.get_work_queue(page=page, page_size=page_size)

    return WorkQueueResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
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
