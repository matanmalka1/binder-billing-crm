from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.binders.schemas.binder import BinderReceiveRequest, BinderResponse, BinderReturnRequest
from app.binders.services.binder_service import BinderService
from app.binders.services.signals_service import SignalsService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.api.binders_common import fetch_client_and_build_response

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("/receive", response_model=BinderResponse, status_code=status.HTTP_201_CREATED)
def receive_binder(request: BinderReceiveRequest, db: DBSession, user: CurrentUser):
    """Receive new binder (intake flow)."""
    service = BinderService(db)
    signals_service = SignalsService(db)
    binder = service.receive_binder(
        client_id=request.client_id,
        binder_number=request.binder_number,
        binder_type=request.binder_type,
        received_at=request.received_at,
        received_by=request.received_by,
        notes=request.notes,
    )
    return fetch_client_and_build_response(binder, db, signals_service)


@router.post("/{binder_id}/ready", response_model=BinderResponse)
def mark_ready_for_pickup(binder_id: int, db: DBSession, user: CurrentUser):
    """Mark binder as ready for pickup."""
    service = BinderService(db)
    signals_service = SignalsService(db)

    binder = service.mark_ready_for_pickup(binder_id=binder_id, user_id=user.id)
    return fetch_client_and_build_response(binder, db, signals_service)


@router.post("/{binder_id}/return", response_model=BinderResponse)
def return_binder(
    binder_id: int,
    db: DBSession,
    user: CurrentUser,
    request: Optional[BinderReturnRequest] = None,
):
    """Return binder to client."""
    service = BinderService(db)
    signals_service = SignalsService(db)

    pickup_person_name = (
        request.pickup_person_name.strip()
        if request and request.pickup_person_name and request.pickup_person_name.strip()
        else user.full_name
    )
    returned_by = request.returned_by if request and request.returned_by is not None else user.id

    binder = service.return_binder(
        binder_id=binder_id,
        pickup_person_name=pickup_person_name,
        returned_by=returned_by,
    )
    return fetch_client_and_build_response(binder, db, signals_service)
