from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_schemas import (
    BusinessCreateRequest,
    BusinessResponse,
    BusinessUpdateRequest,
    ClientBusinessesResponse,
)
from app.businesses.services.business_service import BusinessService
from app.businesses.services.business_guards import assert_business_belongs_to_legal_entity
from app.businesses.models.business import Business
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.core.exceptions import NotFoundError
from app.actions.action_contracts import get_business_actions


def _assert_business_belongs_to_client(db: Session, business: Business, client_id: int) -> None:
    client = ClientRepository(db).get_by_id(client_id)
    legal_entity = (
        LegalEntityRepository(db).get_by_id_number(client.id_number_type, client.id_number)
        if client
        else None
    )
    if not legal_entity:
        raise NotFoundError(f"עסק {business.id} לא נמצא", "BUSINESS.NOT_FOUND")
    assert_business_belongs_to_legal_entity(business, legal_entity.id)


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
def create_business(client_id: int, request: BusinessCreateRequest, db: DBSession, user: CurrentUser):
    """יצירת עסק חדש תחת לקוח קיים (ADVISOR only)."""
    business = BusinessService(db).create_business(
        client_id=client_id,
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
    service = BusinessService(db)
    items, total = service.list_businesses_for_client(client_id, page=page, page_size=page_size)
    return ClientBusinessesResponse(
        client_id=client_id,
        items=[_to_business_response(b, user.role) for b in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@client_businesses_router.get("/{business_id}", response_model=BusinessResponse)
def get_business(client_id: int, business_id: int, db: DBSession, user: CurrentUser):
    service = BusinessService(db)
    business = service.get_business_or_raise(business_id)
    _assert_business_belongs_to_client(db, business, client_id)
    return _to_business_response(business, user.role)


@client_businesses_router.patch("/{business_id}", response_model=BusinessResponse)
def update_business(
    client_id: int,
    business_id: int,
    request: BusinessUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    business = BusinessService(db).update_business(
        business_id,
        client_id=client_id,
        user_role=user.role,
        actor_id=user.id,
        **request.model_dump(exclude_unset=True),
    )
    return _to_business_response(business, user.role)


@client_businesses_router.delete(
    "/{business_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_business(client_id: int, business_id: int, db: DBSession, user: CurrentUser):
    service = BusinessService(db)
    business = service.get_business_or_raise(business_id)
    _assert_business_belongs_to_client(db, business, client_id)
    service.delete_business(business_id, actor_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@client_businesses_router.post(
    "/{business_id}/restore",
    response_model=BusinessResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_business(client_id: int, business_id: int, db: DBSession, user: CurrentUser):
    service = BusinessService(db)
    # IDOR check: verify business belongs to client before restore
    from app.businesses.repositories.business_repository import BusinessRepository
    repo = BusinessRepository(db)
    existing = repo.get_by_id_including_deleted(business_id)
    if not existing:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
    _assert_business_belongs_to_client(db, existing, client_id)
    business = service.restore_business(business_id, actor_id=user.id, actor_role=user.role)
    return _to_business_response(business, user.role)
