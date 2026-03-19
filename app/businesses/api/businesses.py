from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_schemas import (
    BulkBusinessActionRequest,
    BulkBusinessActionResponse,
    BulkBusinessFailedItem,
    BusinessCreateRequest,
    BusinessListResponse,
    BusinessResponse,
    BusinessUpdateRequest,
    BusinessWithClientResponse,
    ClientBusinessesResponse,
)
from app.businesses.services.business_service import BusinessService
from app.actions.action_contracts import get_business_actions

router = APIRouter(
    tags=["businesses"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _to_business_response(business, user_role: UserRole) -> BusinessResponse:
    response = BusinessResponse.model_validate(business)
    response.available_actions = get_business_actions(business, user_role=user_role)
    return response


def _to_business_with_client_response(
    business, user_role: UserRole
) -> BusinessWithClientResponse:
    response = BusinessWithClientResponse(
        **BusinessResponse.model_validate(business).model_dump(),
        client_full_name=business.client.full_name if hasattr(business, "client") and business.client else "",
        client_id_number=business.client.id_number if hasattr(business, "client") and business.client else "",
    )
    response.available_actions = get_business_actions(business, user_role=user_role)
    return response


# ─── Nested under /clients/{client_id}/businesses ────────────────────────────

client_businesses_router = APIRouter(
    prefix="/clients/{client_id}/businesses",
    tags=["businesses"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@client_businesses_router.post(
    "",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def create_business(
    client_id: int,
    request: BusinessCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """
    יצירת עסק חדש תחת לקוח קיים (ADVISOR only).
    לקוח יכול להחזיק מספר עסקים.
    """
    service = BusinessService(db)
    business = service.create_business(
        client_id=client_id,
        business_type=request.business_type,
        opened_at=request.opened_at,
        business_name=request.business_name,
        notes=request.notes,
        actor_id=user.id,
    )
    return _to_business_response(business, user.role)


@client_businesses_router.get("", response_model=ClientBusinessesResponse)
def list_client_businesses(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
):
    """List all active businesses for a client."""
    service = BusinessService(db)
    items = service.list_businesses_for_client(client_id)
    return ClientBusinessesResponse(
        client_id=client_id,
        items=[_to_business_response(b, user.role) for b in items],
        total=len(items),
    )


# ─── Standalone /businesses ───────────────────────────────────────────────────

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
    """List all businesses with optional filters."""
    service = BusinessService(db)
    items, total = service.list_businesses(
        status=status_filter,
        business_type=business_type,
        search=search or None,
        has_signals=has_signals,
        page=page,
        page_size=page_size,
    )
    return BusinessListResponse(
        items=[_to_business_with_client_response(b, user.role) for b in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@businesses_router.get("/{business_id}", response_model=BusinessResponse)
def get_business(business_id: int, db: DBSession, user: CurrentUser):
    """Get business by ID."""
    service = BusinessService(db)
    business = service.get_business_or_raise(business_id)
    return _to_business_response(business, user.role)


@businesses_router.patch(
    "/{business_id}",
    response_model=BusinessResponse,
)
def update_business(
    business_id: int,
    request: BusinessUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update business fields."""
    service = BusinessService(db)
    business = service.update_business(
        business_id,
        user_role=user.role,
        **request.model_dump(exclude_unset=True),
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="העסק לא נמצא",
        )
    return _to_business_response(business, user.role)


@businesses_router.delete(
    "/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_business(business_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a business (ADVISOR only)."""
    service = BusinessService(db)
    deleted = service.delete_business(business_id, actor_id=user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="העסק לא נמצא",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@businesses_router.post(
    "/{business_id}/restore",
    response_model=BusinessResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_business(business_id: int, db: DBSession, user: CurrentUser):
    """Restore a soft-deleted business (ADVISOR only)."""
    service = BusinessService(db)
    business = service.restore_business(
        business_id,
        actor_id=user.id,
        actor_role=user.role,
    )
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
):
    """Apply freeze/close/activate to multiple businesses (ADVISOR only)."""
    service = BusinessService(db)
    succeeded, failed = service.bulk_update_status(
        business_ids=request.business_ids,
        action=request.action,
        actor_id=user.id,
        actor_role=user.role,
    )
    return BulkBusinessActionResponse(
        succeeded=succeeded,
        failed=[BulkBusinessFailedItem(**f) for f in failed],
    )
