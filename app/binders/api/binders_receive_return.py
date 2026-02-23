from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.binders.schemas.binder import BinderReceiveRequest, BinderResponse, BinderReturnRequest
from app.binders.services.binder_service import BinderService
from app.binders.services.signals_service import SignalsService
from app.clients.repositories.client_repository import ClientRepository
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.api.binders_common import to_binder_response

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

    try:
        binder = service.receive_binder(
            client_id=request.client_id,
            binder_number=request.binder_number,
            binder_type=request.binder_type,
            received_at=request.received_at,
            received_by=request.received_by,
            notes=request.notes,
        )

        client_repo = ClientRepository(db)
        client = client_repo.get_by_id(binder.client_id)

        return to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
            client_name=client.full_name if client else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{binder_id}/ready", response_model=BinderResponse)
def mark_ready_for_pickup(binder_id: int, db: DBSession, user: CurrentUser):
    """Mark binder as ready for pickup."""
    service = BinderService(db)
    signals_service = SignalsService(db)

    try:
        binder = service.mark_ready_for_pickup(binder_id=binder_id, user_id=user.id)
        client_repo = ClientRepository(db)
        client = client_repo.get_by_id(binder.client_id)
        return to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
            client_name=client.full_name if client else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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

    try:
        binder = service.return_binder(
            binder_id=binder_id,
            pickup_person_name=pickup_person_name,
            returned_by=returned_by,
        )
        client_repo = ClientRepository(db)
        client = client_repo.get_by_id(binder.client_id)
        return to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
            client_name=client.full_name if client else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
