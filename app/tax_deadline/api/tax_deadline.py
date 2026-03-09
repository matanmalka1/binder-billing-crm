from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.users.models.user import UserRole
from app.tax_deadline.schemas.tax_deadline import (
    DashboardDeadlinesResponse,
    DeadlineUrgentItem,
    TaxDeadlineCreateRequest,
    TaxDeadlineListResponse,
    TaxDeadlineResponse,
    TaxDeadlineUpdateRequest,
    TimelineEntry,
)
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from app.actions.report_deadline_actions import get_tax_deadline_actions

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

# Safety ceiling for global (non-client-scoped) deadline list.
# Without client_id, all pending deadlines are fetched in memory.
# Known architectural debt — a proper fix requires DB-level pagination.
_GLOBAL_DEADLINE_FETCH_LIMIT = 500


def _build_response(deadline, client_name: Optional[str] = None) -> TaxDeadlineResponse:
    r = TaxDeadlineResponse.model_validate(deadline)
    if client_name is not None:
        r.client_name = client_name
    r.available_actions = get_tax_deadline_actions(deadline)
    return r


@router.post("", response_model=TaxDeadlineResponse, status_code=status.HTTP_201_CREATED)
def create_tax_deadline(
    request: TaxDeadlineCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new tax deadline."""
    service = TaxDeadlineService(db)

    deadline_type = DeadlineType(request.deadline_type)
    deadline = service.create_deadline(
        client_id=request.client_id,
        deadline_type=deadline_type,
        due_date=request.due_date,
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return _build_response(deadline)


@router.get("", response_model=TaxDeadlineListResponse)
def list_tax_deadlines(
    db: DBSession,
    user: CurrentUser,
    client_id: Optional[int] = None,
    deadline_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List tax deadlines with filters."""
    service = TaxDeadlineService(db)

    type_enum = None
    if deadline_type:
        type_enum = DeadlineType(deadline_type)

    if client_id:
        # Client-scoped: naturally bounded, no ceiling needed.
        items = service.get_client_deadlines(client_id, status_filter, type_enum)
    else:
        items = service.list_all_pending()[:_GLOBAL_DEADLINE_FETCH_LIMIT]

    total = len(items)
    offset = (page - 1) * page_size
    paginated = items[offset : offset + page_size]

    client_name_map = service.build_client_name_map(paginated)

    def to_response(d) -> TaxDeadlineResponse:
        return _build_response(d, client_name=client_name_map.get(d.client_id))

    return TaxDeadlineListResponse(
        items=[to_response(d) for d in paginated],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/timeline", response_model=list[TimelineEntry])
def get_timeline(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """Return all deadlines for a client sorted by due_date asc with days_remaining and milestone_label."""
    service = TaxDeadlineService(db)
    entries = service.get_timeline(client_id)
    return [TimelineEntry(**e) for e in entries]


@router.get("/{deadline_id}", response_model=TaxDeadlineResponse)
def get_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Get tax deadline by ID."""
    service = TaxDeadlineService(db)
    deadline = service.get_deadline(deadline_id)
    return _build_response(deadline)


@router.post("/{deadline_id}/complete", response_model=TaxDeadlineResponse)
def complete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Mark deadline as completed."""
    service = TaxDeadlineService(db)

    deadline = service.mark_completed(deadline_id)
    return _build_response(deadline)


@router.put("/{deadline_id}", response_model=TaxDeadlineResponse)
def update_tax_deadline(
    deadline_id: int,
    request: TaxDeadlineUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update editable fields on a tax deadline."""
    service = TaxDeadlineService(db)

    deadline_type = None
    if request.deadline_type:
        deadline_type = DeadlineType(request.deadline_type)

    deadline = service.update_deadline(
        deadline_id,
        deadline_type=deadline_type,
        due_date=request.due_date,
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return _build_response(deadline)


@router.delete("/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Delete a tax deadline."""
    service = TaxDeadlineService(db)
    service.delete_deadline(deadline_id)


@router.get("/dashboard/urgent", response_model=DashboardDeadlinesResponse)
def get_dashboard_deadlines(db: DBSession, user: CurrentUser):
    """Get urgent deadlines for dashboard."""
    service = TaxDeadlineService(db)

    summary = service.get_urgent_deadlines_summary()

    urgent_deadlines = [item["deadline"] for item in summary["urgent"]]
    client_name_map = service.build_client_name_map(urgent_deadlines)

    urgent_items = []
    for item in summary["urgent"]:
        deadline = item["deadline"]
        urgent_items.append(
            DeadlineUrgentItem(
                id=deadline.id,
                client_id=deadline.client_id,
                client_name=client_name_map.get(deadline.client_id) or "לא ידוע",
                deadline_type=deadline.deadline_type.value,
                due_date=deadline.due_date,
                urgency=item["urgency"].value,
                days_remaining=item["days_remaining"],
                payment_amount=float(deadline.payment_amount)
                if deadline.payment_amount
                else None,
            )
        )

    upcoming = [_build_response(d) for d in summary["upcoming"]]

    return DashboardDeadlinesResponse(urgent=urgent_items, upcoming=upcoming)
