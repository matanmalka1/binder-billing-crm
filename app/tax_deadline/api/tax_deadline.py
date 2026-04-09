from typing import Optional

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
from app.clients.repositories.client_repository import ClientRepository
from app.actions.report_deadline_actions import get_tax_deadline_actions

router = APIRouter(
    prefix="/tax-deadlines",
    tags=["tax-deadlines"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _build_response(
    deadline,
    db=None,
    business_name: Optional[str] = None,
    user_role: UserRole | str | None = None,
) -> TaxDeadlineResponse:
    r = TaxDeadlineResponse.model_validate(deadline)
    if db is not None and business_name is None:
        client = ClientRepository(db).get_by_id(deadline.client_id)
        business_name = client.full_name if client else None
    if business_name is not None:
        r.business_name = business_name
    r.available_actions = get_tax_deadline_actions(deadline, user_role=user_role)
    return r


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
        client_id=request.client_id,
        deadline_type=DeadlineType(request.deadline_type),
        due_date=request.due_date,
        period=request.period,
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return _build_response(deadline, db=db, user_role=user.role)


@router.get("/{deadline_id:int}", response_model=TaxDeadlineResponse)
def get_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Get tax deadline by ID."""
    service = TaxDeadlineService(db)
    deadline = service.get_deadline(deadline_id)
    return _build_response(deadline, db=db, user_role=user.role)


@router.post(
    "/{deadline_id:int}/complete",
    response_model=TaxDeadlineResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def complete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Mark deadline as completed."""
    service = TaxDeadlineService(db)
    deadline = service.mark_completed(deadline_id, completed_by=user.id)
    return _build_response(deadline, db=db, user_role=user.role)


@router.post(
    "/{deadline_id:int}/reopen",
    response_model=TaxDeadlineResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def reopen_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Revert a completed deadline back to pending."""
    service = TaxDeadlineService(db)
    deadline = service.reopen_deadline(deadline_id)
    return _build_response(deadline, db=db, user_role=user.role)


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
        payment_amount=request.payment_amount,
        description=request.description,
    )
    return _build_response(deadline, db=db, user_role=user.role)


@router.delete(
    "/{deadline_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_tax_deadline(deadline_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a tax deadline."""
    service = TaxDeadlineService(db)
    service.delete_deadline(deadline_id, deleted_by=user.id)
