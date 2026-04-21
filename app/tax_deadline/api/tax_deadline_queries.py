from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.users.models.user import UserRole
from app.core.api_types import PaginatedResponse
from app.tax_deadline.schemas.tax_deadline import (
    DashboardDeadlinesResponse,
    DeadlineUrgentItem,
    TaxDeadlineListResponse,
    TaxDeadlineResponse,
    TimelineEntry,
)
from app.tax_deadline.services.tax_deadline_query_service import TaxDeadlineQueryService
from app.actions.report_deadline_actions import get_tax_deadline_actions

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _build_response(
    deadline,
    business_name: Optional[str] = None,
    office_client_number: Optional[int] = None,
    user_role: UserRole | str | None = None,
) -> TaxDeadlineResponse:
    r = TaxDeadlineResponse.model_validate(deadline)
    if business_name is not None:
        r.business_name = business_name
    r.office_client_number = office_client_number
    r.available_actions = get_tax_deadline_actions(deadline, user_role=user_role)
    return r


@router.get("", response_model=TaxDeadlineListResponse)
def list_tax_deadlines(
    db: DBSession,
    user: CurrentUser,
    client_record_id: Optional[int] = None,
    business_name: Optional[str] = Query(None),
    client_name: Optional[str] = Query(None),
    deadline_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    due_from: Optional[str] = Query(None, description="סינון מתאריך (YYYY-MM-DD)"),
    due_to: Optional[str] = Query(None, description="סינון עד תאריך (YYYY-MM-DD)"),
    period: Optional[str] = Query(None, description="סינון לפי תקופה (YYYY-MM)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List tax deadlines with optional filters."""
    from datetime import date as date_type
    service = TaxDeadlineQueryService(db)
    type_enum = DeadlineType(deadline_type) if deadline_type else None
    search_name = business_name or client_name

    due_from_date = date_type.fromisoformat(due_from) if due_from else None
    due_to_date = date_type.fromisoformat(due_to) if due_to else None

    paginated, total = service.list_deadlines(
        client_record_id, search_name, status_filter, type_enum, page=page, page_size=page_size,
        due_from=due_from_date, due_to=due_to_date, period=period,
    )

    client_context_map = service.build_client_context_map(paginated)

    return TaxDeadlineListResponse(
        items=[
            _build_response(
                d,
                business_name=client_context_map.get(d.client_record_id, {}).get("full_name"),
                office_client_number=client_context_map.get(d.client_record_id, {}).get("office_client_number"),
                user_role=user.role,
            )
            for d in paginated
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/timeline", response_model=PaginatedResponse[TimelineEntry])
def get_timeline(
    client_record_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Return all deadlines for a client sorted by due_date asc."""
    service = TaxDeadlineQueryService(db)
    all_entries = service.get_timeline(client_record_id)
    total = len(all_entries)
    start = (page - 1) * page_size
    items = [TimelineEntry(**e) for e in all_entries[start:start + page_size]]
    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/dashboard/urgent", response_model=DashboardDeadlinesResponse)
def get_dashboard_deadlines(db: DBSession, user: CurrentUser):
    """Get urgent and upcoming deadlines for the dashboard widget."""
    service = TaxDeadlineQueryService(db)
    summary = service.get_urgent_deadlines_summary()

    urgent_deadlines = [item["deadline"] for item in summary["urgent"]]
    client_context_map = service.build_client_context_map(urgent_deadlines)

    urgent_items = []
    for item in summary["urgent"]:
        deadline = item["deadline"]
        urgent_items.append(
            DeadlineUrgentItem(
                id=deadline.id,
                client_record_id=deadline.client_record_id,
                business_name=client_context_map.get(deadline.client_record_id, {}).get("full_name") or "לא ידוע",
                deadline_type=deadline.deadline_type,
                due_date=deadline.due_date,
                urgency=item["urgency"],
                days_remaining=item["days_remaining"],
                payment_amount=deadline.payment_amount,
            )
        )

    upcoming_client_context_map = service.build_client_context_map(summary["upcoming"])
    upcoming = [
        _build_response(
            d,
            business_name=upcoming_client_context_map.get(d.client_record_id, {}).get("full_name"),
            office_client_number=upcoming_client_context_map.get(d.client_record_id, {}).get("office_client_number"),
            user_role=user.role,
        )
        for d in summary["upcoming"]
    ]
    return DashboardDeadlinesResponse(urgent=urgent_items, upcoming=upcoming)
