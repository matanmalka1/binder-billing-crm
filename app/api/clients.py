from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas import (
    ClientCreateRequest,
    ClientUpdateRequest,
    ClientResponse,
    ClientListResponse,
)
from app.services import ClientService

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


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
        return ClientResponse.model_validate(client)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=ClientListResponse)
def list_clients(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List clients with pagination."""
    service = ClientService(db)
    items, total = service.list_clients(status=status_filter, page=page, page_size=page_size)

    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in items],
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

    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    request: ClientUpdateRequest,
    db: DBSession,
    user: CurrentUser,
):
    """Update client. Status changes (freeze/close) require advisor role."""
    service = ClientService(db)
    
    update_data = request.model_dump(exclude_unset=True)
    
    # Freeze/close operations restricted to advisor only
    if "status" in update_data and update_data["status"] in ["frozen", "closed"]:
        if user.role != UserRole.ADVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only advisors can freeze or close clients"
            )
    
    client = service.update_client(client_id, **update_data)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return ClientResponse.model_validate(client)
