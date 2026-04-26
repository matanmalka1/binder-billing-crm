from fastapi import APIRouter, Depends, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.users.models.user import UserRole
from app.tax_deadline.schemas.tax_deadline import (
    TaxDeadlineCreateRequest,
    TaxDeadlineResponse,
    TaxDeadlineUpdateRequest,
)
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from app.tax_deadline.services.response_builder import TaxDeadlineResponseBuilder

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)

@router.post(
    "",
    response_model=TaxDeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_tax_deadline(
    request: TaxDeadlineCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Create new tax deadline."""
    service = TaxDeadlineService(db)
    deadline = service.create_deadline(
        client_record_id=request.client_record_id,
        deadline_type=DeadlineType(request.deadline_type),
        due_date=request.due_date,
        period=request.period,
        tax_year=request.tax_year,
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return TaxDeadlineResponseBuilder(db).build(deadline, user_role=user.role)


@router.get("/{deadline_id:int}", response_model=TaxDeadlineResponse)
def get_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Get tax deadline by ID."""
    service = TaxDeadlineService(db)
    deadline = service.get_deadline(deadline_id)
    return TaxDeadlineResponseBuilder(db).build(deadline, user_role=user.role)


@router.post(
    "/{deadline_id:int}/complete",
    response_model=TaxDeadlineResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def complete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Mark deadline as completed."""
    service = TaxDeadlineService(db)
    deadline = service.mark_completed(deadline_id, completed_by=user.id)
    return TaxDeadlineResponseBuilder(db).build(deadline, user_role=user.role)


@router.post(
    "/{deadline_id:int}/reopen",
    response_model=TaxDeadlineResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def reopen_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Revert a completed deadline back to pending."""
    service = TaxDeadlineService(db)
    deadline = service.reopen_deadline(deadline_id)
    return TaxDeadlineResponseBuilder(db).build(deadline, user_role=user.role)


@router.put(
    "/{deadline_id:int}",
    response_model=TaxDeadlineResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def update_tax_deadline(
    deadline_id: int,
    request: TaxDeadlineUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update editable fields on a tax deadline."""
    service = TaxDeadlineService(db)
    deadline_type = DeadlineType(request.deadline_type) if request.deadline_type else None
    deadline = service.update_deadline(
        deadline_id,
        deadline_type=deadline_type,
        due_date=request.due_date,
        period=request.period,
        tax_year=request.tax_year,
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return TaxDeadlineResponseBuilder(db).build(deadline, user_role=user.role)


@router.delete(
    "/{deadline_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a tax deadline."""
    service = TaxDeadlineService(db)
    service.delete_deadline(deadline_id, deleted_by=user.id)
