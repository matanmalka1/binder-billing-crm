from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

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

    try:
        charge = service.create_charge(
            client_id=request.client_id,
            amount=request.amount,
            charge_type=request.charge_type,
            period=request.period,
            currency=request.currency,
            actor_id=user.id,
        )
        return ChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{charge_id}/issue",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def issue_charge(charge_id: int, db: DBSession, user: CurrentUser):
    """Issue a draft charge (ADVISOR only)."""
    service = BillingService(db)

    try:
        charge = service.issue_charge(charge_id, actor_id=user.id)
        return ChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{charge_id}/mark-paid",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def mark_charge_paid(charge_id: int, db: DBSession, user: CurrentUser):
    """Mark issued charge as paid (ADVISOR only)."""
    service = BillingService(db)

    try:
        charge = service.mark_charge_paid(charge_id, actor_id=user.id)
        return ChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{charge_id}/cancel",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def cancel_charge(charge_id: int, db: DBSession, user: CurrentUser, request: ChargeCancelRequest = Body(default_factory=ChargeCancelRequest)):
    """Cancel a charge (ADVISOR only)."""
    service = BillingService(db)

    try:
        charge = service.cancel_charge(charge_id, actor_id=user.id, reason=request.reason)
        return ChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    items, total, client_name_map = service.list_charges(
        client_id=client_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    def _enrich(charge, schema):
        data = schema.model_validate(charge).model_dump()
        data["client_name"] = client_name_map.get(charge.client_id)
        return schema(**data)

    # Secretary sees limited view
    if user.role == UserRole.SECRETARY:
        return ChargeListResponse(
            items=[_enrich(c, ChargeResponseSecretary) for c in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    # Advisor sees full view
    return ChargeListResponse(
        items=[_enrich(c, ChargeResponse) for c in items],
        page=page,
        page_size=page_size,
        total=total,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Charge not found"
        )

    if user.role == UserRole.SECRETARY:
        return ChargeResponseSecretary.model_validate(charge)

    return ChargeResponse.model_validate(charge)
