from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.charge.schemas.charge import BulkChargeActionRequest, BulkChargeActionResponse, ChargeCancelRequest, ChargeCreateRequest, ChargeListResponse, ChargeResponse, ChargeResponseSecretary
from app.charge.services.billing_service import BillingService
from app.charge.services.bulk_billing_service import BulkBillingService
from app.charge.services.charge_query_service import ChargeQueryService


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
    charge = BillingService(db).create_charge(
        business_id=request.business_id,
        amount=request.amount,
        charge_type=request.charge_type,
        period=request.period,
        actor_id=user.id,
    )
    data = ChargeResponse.model_validate(charge).model_dump()
    data["business_name"] = ChargeQueryService(db).enrich_business_name(charge)
    return ChargeResponse(**data)


@router.post(
    "/{charge_id}/issue",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def issue_charge(charge_id: int, db: DBSession, user: CurrentUser):
    """Issue a draft charge (ADVISOR only)."""
    charge = BillingService(db).issue_charge(charge_id, actor_id=user.id)
    data = ChargeResponse.model_validate(charge).model_dump()
    data["business_name"] = ChargeQueryService(db).enrich_business_name(charge)
    return ChargeResponse(**data)


@router.post(
    "/{charge_id}/mark-paid",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def mark_charge_paid(charge_id: int, db: DBSession, user: CurrentUser):
    """Mark issued charge as paid (ADVISOR only)."""
    charge = BillingService(db).mark_charge_paid(charge_id, actor_id=user.id)
    data = ChargeResponse.model_validate(charge).model_dump()
    data["business_name"] = ChargeQueryService(db).enrich_business_name(charge)
    return ChargeResponse(**data)


@router.post(
    "/{charge_id}/cancel",
    response_model=ChargeResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def cancel_charge(charge_id: int, db: DBSession, user: CurrentUser, request: ChargeCancelRequest = Body(default_factory=ChargeCancelRequest)):
    """Cancel a charge (ADVISOR only)."""
    charge = BillingService(db).cancel_charge(charge_id, actor_id=user.id, reason=request.reason)
    data = ChargeResponse.model_validate(charge).model_dump()
    data["business_name"] = ChargeQueryService(db).enrich_business_name(charge)
    return ChargeResponse(**data)


@router.get(
    "",
    response_model=ChargeListResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def list_charges(
    db: DBSession,
    user: CurrentUser,
    business_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    charge_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List charges with role-based data filtering."""
    return ChargeQueryService(db).list_charges_for_role(
        user_role=user.role,
        business_id=business_id,
        status=status_filter,
        charge_type=charge_type,
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
    charge = BillingService(db).get_charge(charge_id)
    client_name = ChargeQueryService(db).enrich_business_name(charge)

    if user.role == UserRole.SECRETARY:
        data = ChargeResponseSecretary.model_validate(charge).model_dump()
        data["business_name"] = client_name
        return ChargeResponseSecretary(**data)

    data = ChargeResponse.model_validate(charge).model_dump()
    data["business_name"] = client_name
    return ChargeResponse(**data)


@router.post(
    "/bulk-action",
    response_model=BulkChargeActionResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def bulk_charge_action(
    request: BulkChargeActionRequest,
    db: DBSession,
    user: CurrentUser,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    """Apply action to multiple charges in bulk (ADVISOR only)."""
    service = BulkBillingService(db)
    succeeded, failed = service.bulk_action(
        charge_ids=request.charge_ids,
        action=request.action,
        actor_id=user.id,
        cancellation_reason=request.cancellation_reason,
    )
    return BulkChargeActionResponse(succeeded=succeeded, failed=failed)


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
