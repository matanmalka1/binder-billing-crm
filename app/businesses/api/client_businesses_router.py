from fastapi import APIRouter, Depends, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_schemas import (
    BusinessCreateRequest,
    BusinessResponse,
    ClientBusinessesResponse,
)
from app.businesses.services.business_service import BusinessService
from app.actions.action_contracts import get_business_actions


def _to_business_response(business, user_role: UserRole) -> BusinessResponse:
    response = BusinessResponse.model_validate(business)
    response.available_actions = get_business_actions(business, user_role=user_role)
    return response


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
    """יצירת עסק חדש תחת לקוח קיים (ADVISOR only)."""
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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List active businesses for a client."""
    service = BusinessService(db)
    items, total = service.list_businesses_for_client(client_id, page=page, page_size=page_size)
    return ClientBusinessesResponse(
        client_id=client_id,
        items=[_to_business_response(b, user.role) for b in items],
        page=page,
        page_size=page_size,
        total=total,
    )
