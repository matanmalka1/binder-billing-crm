from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.users.models.user import UserRole
from app.tax_deadline.schemas.tax_deadline import (
    DashboardDeadlinesResponse,
    DeadlineUrgentItem,
    TaxDeadlineCreateRequest,
    TaxDeadlineListResponse,
    TaxDeadlineResponse,
)
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("", response_model=TaxDeadlineResponse, status_code=status.HTTP_201_CREATED)
def create_tax_deadline(
    request: TaxDeadlineCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new tax deadline."""
    service = TaxDeadlineService(db)

    try:
        deadline_type = DeadlineType(request.deadline_type)
        deadline = service.create_deadline(
            client_id=request.client_id,
            deadline_type=deadline_type,
            due_date=request.due_date,
            payment_amount=request.payment_amount,
            description=request.description,
        )
        return TaxDeadlineResponse.model_validate(deadline)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        try:
            type_enum = DeadlineType(deadline_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid deadline type: {deadline_type}",
            )

    if client_id:
        items = service.get_client_deadlines(client_id, status_filter, type_enum)
    else:
        items = service.deadline_repo.list_pending_due_by_date(
            date.today(),
            date(2099, 12, 31),
        )

    total = len(items)
    offset = (page - 1) * page_size
    paginated = items[offset : offset + page_size]

    return TaxDeadlineListResponse(
        items=[TaxDeadlineResponse.model_validate(d) for d in paginated],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{deadline_id}", response_model=TaxDeadlineResponse)
def get_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Get tax deadline by ID."""
    service = TaxDeadlineService(db)
    deadline = service.deadline_repo.get_by_id(deadline_id)

    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax deadline not found",
        )

    return TaxDeadlineResponse.model_validate(deadline)


@router.post("/{deadline_id}/complete", response_model=TaxDeadlineResponse)
def complete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Mark deadline as completed."""
    service = TaxDeadlineService(db)

    try:
        deadline = service.mark_completed(deadline_id)
        return TaxDeadlineResponse.model_validate(deadline)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/dashboard/urgent", response_model=DashboardDeadlinesResponse)
def get_dashboard_deadlines(db: DBSession, user: CurrentUser):
    """Get urgent deadlines for dashboard."""
    service = TaxDeadlineService(db)
    from app.clients.repositories.client_repository import ClientRepository

    client_repo = ClientRepository(db)

    summary = service.get_urgent_deadlines_summary()

    urgent_items = []
    for item in summary["urgent"]:
        deadline = item["deadline"]
        client = client_repo.get_by_id(deadline.client_id)

        urgent_items.append(
            DeadlineUrgentItem(
                id=deadline.id,
                client_id=deadline.client_id,
                client_name=client.full_name if client else "Unknown",
                deadline_type=deadline.deadline_type.value,
                due_date=deadline.due_date,
                urgency=item["urgency"].value,
                days_remaining=item["days_remaining"],
                payment_amount=float(deadline.payment_amount)
                if deadline.payment_amount
                else None,
            )
        )

    upcoming = [TaxDeadlineResponse.model_validate(d) for d in summary["upcoming"]]

    return DashboardDeadlinesResponse(urgent=urgent_items, upcoming=upcoming)
