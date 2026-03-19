from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.schemas.client import (
    BulkClientActionRequest,
    BulkClientActionResponse,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    DeletedClientInfo,
)
from app.clients.services.client_service import ClientService
from app.clients.services.client_lookup import get_client_or_raise
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
    """Create new client. Pass force=true to create even if a deleted record exists."""
    service = ClientService(db)
    client = service.create_client(
        full_name=request.full_name,
        id_number=request.id_number,
        client_type=request.client_type,
        opened_at=request.opened_at,
        phone=request.phone,
        email=request.email,
        actor_id=user.id,
        force=request.force,
    )
    return _to_client_response(client, user.role)


@router.post(
    "/{client_id}/restore",
    response_model=ClientResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def restore_client(client_id: int, db: DBSession, user: CurrentUser):
    """Restore a soft-deleted client (ADVISOR only)."""
    service = ClientService(db)
    client = service.restore_client(
        client_id=client_id,
        actor_id=user.id,
        actor_role=user.role,
    )
    return _to_client_response(client, user.role)


@router.get("/deleted/{id_number}", response_model=Optional[DeletedClientInfo])
def get_deleted_client_by_id_number(
    id_number: str,
    db: DBSession,
    user: CurrentUser,
):
    """Return the most recently deleted client for a given ID number, or null if none."""
    service = ClientService(db)
    deleted = service.client_repo.get_deleted_by_id_number(id_number)
    if not deleted:
        return None
    return DeletedClientInfo.model_validate(deleted)


@router.get("", response_model=ClientListResponse)
def list_clients(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    has_signals: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with pagination."""
    service = ClientService(db)
    items, total = service.list_clients(
        status=status_filter,
        has_signals=has_signals,
        search=search or None,
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
    client = get_client_or_raise(db, client_id)
    return _to_client_response(client, user.role)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    request: ClientUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update client. Authorization enforced in service layer."""
    service = ClientService(db)
    update_data = request.model_dump(exclude_unset=True)
    client = service.update_client(client_id, user.role, **update_data)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הלקוח לא נמצא")
    return _to_client_response(client, user.role)


@router.post(
    "/bulk-action",
    response_model=BulkClientActionResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def bulk_client_action(request: BulkClientActionRequest, db: DBSession, user: CurrentUser):
    """Apply freeze/close/activate to multiple clients (ADVISOR only)."""
    service = ClientService(db)
    succeeded, failed = service.bulk_update_status(
        client_ids=request.client_ids,
        action=request.action,
        actor_id=user.id,
        actor_role=user.role,
    )
    return BulkClientActionResponse(succeeded=succeeded, failed=failed)


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_client(client_id: int, db: DBSession, user: CurrentUser):
    """Soft-delete a client (ADVISOR only)."""
    service = ClientService(db)
    deleted = service.delete_client(client_id, actor_id=user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="הלקוח לא נמצא")
    return Response(status_code=status.HTTP_204_NO_CONTENT)