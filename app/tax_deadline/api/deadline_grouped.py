"""Grouped deadline endpoints — aggregate view for the main מועדים page."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.core.api_types import PaginatedResponse
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.schemas.tax_deadline import TaxDeadlineResponse
from app.tax_deadline.schemas.grouped_deadline import DeadlineGroup, GroupedDeadlineListResponse
from app.tax_deadline.services.grouped_deadline_service import GroupedDeadlineService

router = APIRouter(
    prefix="/tax-deadlines/grouped",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=GroupedDeadlineListResponse)
def list_grouped_deadlines(
    db: DBSession,
    user: CurrentUser,
    status: Optional[str] = Query(None),
    deadline_type: Optional[str] = Query(None),
    due_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    due_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    client_name: Optional[str] = Query(None),
):
    """Return deadline groups for the main מועדים page.

    Groups raw client deadlines by (type × period × due_date).
    Default window: today + 90 days. Max 200 groups.
    """
    from datetime import date as date_type

    service = GroupedDeadlineService(db)
    type_enum = DeadlineType(deadline_type) if deadline_type else None
    due_from_date = date_type.fromisoformat(due_from) if due_from else None
    due_to_date = date_type.fromisoformat(due_to) if due_to else None

    return service.list_groups(
        status=status,
        deadline_type=type_enum,
        due_from=due_from_date,
        due_to=due_to_date,
        client_name=client_name,
    )


@router.get("/{group_key}/clients", response_model=PaginatedResponse[TaxDeadlineResponse])
def get_group_clients(
    group_key: str,
    db: DBSession,
    user: CurrentUser,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Return paginated per-client deadlines for a deadline group (drill-down)."""
    service = GroupedDeadlineService(db)
    items, total = service.get_group_clients(
        group_key,
        status=status,
        page=page,
        page_size=page_size,
        user_role=user.role,
    )
    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)
