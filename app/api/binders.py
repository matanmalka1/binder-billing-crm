from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas import BinderReceiveRequest, BinderReturnRequest, BinderResponse, BinderListResponse
from app.services import BinderService

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("/receive", response_model=BinderResponse, status_code=status.HTTP_201_CREATED)
def receive_binder(request: BinderReceiveRequest, db: DBSession, user: CurrentUser):
    """Receive new binder (intake flow)."""
    service = BinderService(db)

    try:
        binder = service.receive_binder(
            client_id=request.client_id,
            binder_number=request.binder_number,
            received_at=request.received_at,
            received_by=request.received_by,
            notes=request.notes,
        )

        response = BinderResponse.model_validate(binder)
        response.days_in_office = (date.today() - binder.received_at).days
        return response

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{binder_id}/return", response_model=BinderResponse)
def return_binder(binder_id: int, request: BinderReturnRequest, db: DBSession, user: CurrentUser):
    """Return binder to client."""
    service = BinderService(db)

    try:
        binder = service.return_binder(
            binder_id=binder_id,
            pickup_person_name=request.pickup_person_name,
            returned_by=request.returned_by,
        )
        return BinderResponse.model_validate(binder)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = None,
):
    """List active binders with optional filters."""
    service = BinderService(db)
    binders = service.list_active_binders(client_id=client_id, status=status_filter)

    items = []
    for binder in binders:
        response = BinderResponse.model_validate(binder)
        response.days_in_office = (date.today() - binder.received_at).days
        items.append(response)

    return BinderListResponse(items=items)


@router.get("/{binder_id}", response_model=BinderResponse)
def get_binder(binder_id: int, db: DBSession, user: CurrentUser):
    """Get binder by ID."""
    service = BinderService(db)
    binder = service.get_binder(binder_id)

    if not binder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binder not found")

    response = BinderResponse.model_validate(binder)
    response.days_in_office = (date.today() - binder.received_at).days
    return response
