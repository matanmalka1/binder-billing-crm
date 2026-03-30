from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.users.models.user import UserRole
from app.tax_deadline.schemas.tax_deadline import (
    DashboardDeadlinesResponse,
    DeadlineUrgentItem,
    TaxDeadlineListResponse,
    TaxDeadlineResponse,
    TimelineEntry,
)
from app.tax_deadline.services.tax_deadline_query_service import TaxDeadlineQueryService
from app.tax_deadline.services.constants import GLOBAL_DEADLINE_FETCH_LIMIT
from app.actions.report_deadline_actions import get_tax_deadline_actions

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _build_response(
    deadline,
    business_name: Optional[str] = None,
    client_id: Optional[int] = None,
) -> TaxDeadlineResponse:
    r = TaxDeadlineResponse.model_validate(deadline)
    if business_name is not None:
        r.business_name = business_name
    if client_id is not None:
        r.client_id = client_id
    r.available_actions = get_tax_deadline_actions(deadline)
    return r


@router.get("", response_model=TaxDeadlineListResponse)
def list_tax_deadlines(
    db: DBSession,
    user: CurrentUser,
    business_id: Optional[int] = None,
    client_name: Optional[str] = Query(None),
    deadline_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List tax deadlines with optional filters."""
    service = TaxDeadlineQueryService(db)
    type_enum = DeadlineType(deadline_type) if deadline_type else None

    if business_id:
        from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
        items = TaxDeadlineService(db).get_business_deadlines(business_id, status_filter, type_enum)
    elif client_name:
        items = service.get_deadlines_by_client_name(client_name, status_filter, type_enum)
    else:
        items = service.list_all_pending()[:GLOBAL_DEADLINE_FETCH_LIMIT]

    total = len(items)
    offset = (page - 1) * page_size
    paginated = items[offset: offset + page_size]

    business_name_map = service.build_business_name_map(paginated)
    client_id_map = service.build_client_id_map(paginated)

    return TaxDeadlineListResponse(
        items=[
            _build_response(
                d,
                business_name=business_name_map.get(d.business_id),
                client_id=client_id_map.get(d.business_id),
            )
            for d in paginated
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/timeline", response_model=list[TimelineEntry])
def get_timeline(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Return all deadlines for a business sorted by due_date asc."""
    service = TaxDeadlineQueryService(db)
    entries = service.get_timeline(business_id)
    return [TimelineEntry(**e) for e in entries]


@router.get("/dashboard/urgent", response_model=DashboardDeadlinesResponse)
def get_dashboard_deadlines(db: DBSession, user: CurrentUser):
    """Get urgent and upcoming deadlines for the dashboard widget."""
    service = TaxDeadlineQueryService(db)
    summary = service.get_urgent_deadlines_summary()

    urgent_deadlines = [item["deadline"] for item in summary["urgent"]]
    business_name_map = service.build_business_name_map(urgent_deadlines)

    urgent_items = []
    for item in summary["urgent"]:
        deadline = item["deadline"]
        urgent_items.append(
            DeadlineUrgentItem(
                id=deadline.id,
                business_id=deadline.business_id,
                business_name=business_name_map.get(deadline.business_id) or "לא ידוע",
                deadline_type=deadline.deadline_type,
                due_date=deadline.due_date,
                urgency=item["urgency"],
                days_remaining=item["days_remaining"],
                payment_amount=float(deadline.payment_amount) if deadline.payment_amount else None,
            )
        )

    upcoming = [_build_response(d) for d in summary["upcoming"]]
    return DashboardDeadlinesResponse(urgent=urgent_items, upcoming=upcoming)
