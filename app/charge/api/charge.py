from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.charge.schemas.charge import ChargeCancelRequest, ChargeCreateRequest, ChargeListResponse, ChargeResponse, ChargeResponseSecretary
from app.charge.services.billing_service import BillingService


router = APIRouter(
    prefix="/charges",
    tags=["charges"],
)


@router.post(
    "",
    response_model=ChargeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_charge(request: ChargeCreateRequest, db: DBSession, user: CurrentUser):
    """Create new charge (ADVISOR only)."""
    service = BillingService(db)

    charge = service.create_charge(
        client_id=request.client_id,
        amount=request.amount,
        charge_type=request.charge_type,
        period=request.period,
        currency=request.currency,
        actor_id=user.id,
    )
    return ChargeResponse.model_validate(charge)


@router.post(
    "/{charge_id}/issue",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def issue_charge(charge_id: int, db: DBSession, user: CurrentUser):
    """Issue a draft charge (ADVISOR only)."""
    service = BillingService(db)

    charge = service.issue_charge(charge_id, actor_id=user.id)
    return ChargeResponse.model_validate(charge)


@router.post(
    "/{charge_id}/mark-paid",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def mark_charge_paid(charge_id: int, db: DBSession, user: CurrentUser):
    """Mark issued charge as paid (ADVISOR only)."""
    service = BillingService(db)

    charge = service.mark_charge_paid(charge_id, actor_id=user.id)
    return ChargeResponse.model_validate(charge)


@router.post(
    "/{charge_id}/cancel",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def cancel_charge(charge_id: int, db: DBSession, user: CurrentUser, request: ChargeCancelRequest = Body(default_factory=ChargeCancelRequest)):
    """Cancel a charge (ADVISOR only)."""
    service = BillingService(db)

    charge = service.cancel_charge(charge_id, actor_id=user.id, reason=request.reason)
    return ChargeResponse.model_validate(charge)


@router.get(
    "",
    response_model=ChargeListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_charges(
    db: DBSession,
    user: CurrentUser,
    client_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List charges with role-based data filtering."""
    service = BillingService(db)
    return service.list_charges_for_role(
        user_role=user.role,
        client_id=client_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/{charge_id}",
    response_model=ChargeResponse | ChargeResponseSecretary,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_charge(charge_id: int, db: DBSession, user: CurrentUser):
    """Get charge by ID (authenticated users)."""
    service = BillingService(db)
    charge = service.get_charge(charge_id)

    if not charge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="החיוב לא נמצא"
        )

    if user.role == UserRole.SECRETARY:
        return ChargeResponseSecretary.model_validate(charge)

    return ChargeResponse.model_validate(charge)


@router.delete(
    "/{charge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_charge(charge_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a draft charge (ADVISOR only)."""
    service = BillingService(db)
    service.delete_charge(charge_id, actor_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
