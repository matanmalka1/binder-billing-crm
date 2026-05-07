from fastapi import APIRouter, Depends, Query

from app.common.enums import ObligationType
from app.tax_calendar.schemas.grouped import (
    TaxCalendarGroupItemsResponse,
    TaxCalendarGroupResponse,
)
from app.tax_calendar.services.grouped_items_service import get_group_items
from app.tax_calendar.services.grouped_service import list_groups
from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(prefix="/tax-calendar", tags=["tax-calendar"])


@router.get(
    "/groups",
    response_model=list[TaxCalendarGroupResponse],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_tax_calendar_groups(
    db: DBSession,
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
    obligation_type: ObligationType | None = Query(None),
    include_empty: bool = Query(False),
):
    return list_groups(
        db,
        start_year=start_year,
        end_year=end_year,
        obligation_type=obligation_type,
        include_empty=include_empty,
    )


@router.get(
    "/groups/{tax_calendar_entry_id}/items",
    response_model=TaxCalendarGroupItemsResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_tax_calendar_group_items(
    tax_calendar_entry_id: int,
    db: DBSession,
):
    return get_group_items(db, tax_calendar_entry_id)
