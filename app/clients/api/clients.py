from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.schemas.client import (
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
)
from app.clients.services.client_service import ClientService
from app.actions.action_contracts import get_client_actions

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _to_client_response(client, user_role: UserRole) -> ClientResponse:
    response = ClientResponse.model_validate(client)
    response.available_actions = get_client_actions(client, user_role=user_role)
    return response


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(request: ClientCreateRequest, db: DBSession, user: CurrentUser):
    """Create new client."""
    service = ClientService(db)

    try:
        client = service.create_client(
            full_name=request.full_name,
            id_number=request.id_number,
            client_type=request.client_type,
            opened_at=request.opened_at,
            phone=request.phone,
            email=request.email,
        )
        return _to_client_response(client, user.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=ClientListResponse)
def list_clients(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    has_signals: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with pagination."""
    service = ClientService(db)
    items, total = service.list_clients(
        status=status_filter,
        has_signals=has_signals,
        page=page,
        page_size=page_size,
    )

    return ClientListResponse(
        items=[_to_client_response(c, user.role) for c in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: DBSession, user: CurrentUser):
    """Get client by ID."""
    service = ClientService(db)
    client = service.get_client(client_id)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return _to_client_response(client, user.role)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    request: ClientUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """
    Update client.

    Sprint 6 cleanup: Authorization moved to service layer.
    """
    service = ClientService(db)

    update_data = request.model_dump(exclude_unset=True)

    try:
        # Sprint 6: Pass user role to service for authorization
        client = service.update_client(client_id, user.role, **update_data)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return _to_client_response(client, user.role)
