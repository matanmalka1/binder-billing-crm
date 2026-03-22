from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_schemas import (
    BulkBusinessActionRequest,
    BulkBusinessActionResponse,
    BulkBusinessFailedItem,
    BusinessListResponse,
    BusinessResponse,
    BusinessUpdateRequest,
    BusinessWithClientResponse,
)
from app.businesses.services.business_service import BusinessService
from app.actions.action_contracts import get_business_actions

# Re-export so router_registry can import both from this module.
from app.businesses.api.client_businesses_router import client_businesses_router  # noqa: F401


def _to_business_response(business, user_role: UserRole) -> BusinessResponse:
    response = BusinessResponse.model_validate(business)
    response.available_actions = get_business_actions(business, user_role=user_role)
    return response


def _to_business_with_client_response(business, user_role: UserRole) -> BusinessWithClientResponse:
    response = BusinessWithClientResponse(
        **BusinessResponse.model_validate(business).model_dump(),
        client_full_name=business.client.full_name if business.client else "",
        client_id_number=business.client.id_number if business.client else "",
    )
    response.available_actions = get_business_actions(business, user_role=user_role)
    return response


businesses_router = APIRouter(
    prefix="/businesses",
    tags=["businesses"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@businesses_router.get("", response_model=BusinessListResponse)
def list_businesses(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    business_type: Optional[str] = Query(None),
    has_signals: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = BusinessService(db)
    items, total = service.list_businesses(
        status=status_filter, business_type=business_type,
        search=search or None, has_signals=has_signals,
        page=page, page_size=page_size,
    )
    return BusinessListResponse(
        items=[_to_business_with_client_response(b, user.role) for b in items],
        page=page, page_size=page_size, total=total,
    )


@businesses_router.get("/{business_id}", response_model=BusinessResponse)
def get_business(business_id: int, db: DBSession, user: CurrentUser):
    service = BusinessService(db)
    return _to_business_response(service.get_business_or_raise(business_id), user.role)


@businesses_router.patch("/{business_id}", response_model=BusinessResponse)
def update_business(business_id: int, request: BusinessUpdateRequest, db: DBSession, user: CurrentUser):
    service = BusinessService(db)
    business = service.update_business(
        business_id, user_role=user.role, **request.model_dump(exclude_unset=True),
    )
    return _to_business_response(business, user.role)


@businesses_router.delete(
    "/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_business(business_id: int, db: DBSession, user: CurrentUser):
    BusinessService(db).delete_business(business_id, actor_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@businesses_router.post(
    "/{business_id}/restore",
    response_model=BusinessResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_business(business_id: int, db: DBSession, user: CurrentUser):
    business = BusinessService(db).restore_business(business_id, actor_id=user.id, actor_role=user.role)
    return _to_business_response(business, user.role)


@businesses_router.post(
    "/bulk-action",
    response_model=BulkBusinessActionResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def bulk_business_action(
    request: BulkBusinessActionRequest,
    db: DBSession,
    user: CurrentUser,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    """Apply freeze/close/activate to multiple businesses (ADVISOR only)."""
    succeeded, failed = BusinessService(db).bulk_update_status(
        business_ids=request.business_ids,
        action=request.action,
        actor_id=user.id,
        actor_role=user.role,
    )
    return BulkBusinessActionResponse(
        succeeded=succeeded,
        failed=[BulkBusinessFailedItem(**f) for f in failed],
    )
