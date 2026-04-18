from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.binders.schemas.binder import (
    BinderHandoverRequest,
    BinderHandoverResponse,
    BinderMarkReadyBulkRequest,
    BinderReceiveRequest,
    BinderResponse,
    BinderReturnRequest,
    BinderIntakeResponse,
    BinderReceiveResult,
)
from app.binders.services.binder_service import BinderService
from app.binders.services.binder_handover_service import BinderHandoverService
from app.binders.repositories.binder_handover_repository import BinderHandoverRepository
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.binders.api.binders_common import fetch_client_and_build_response

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.post("/receive", response_model=BinderReceiveResult, status_code=status.HTTP_201_CREATED)
def receive_binder(request: BinderReceiveRequest, db: DBSession, user: CurrentUser):
    """Receive material into existing binder or create new one."""
    service = BinderService(db)
    materials = [m.model_dump() for m in request.materials] if request.materials else []
    binder, intake, is_new_binder = service.receive_binder(
        client_id=request.client_id,
        open_new_binder=request.open_new_binder,
        received_at=request.received_at,
        received_by=request.received_by,
        notes=request.notes,
        materials=materials,
    )
    binder_resp = fetch_client_and_build_response(binder, db)
    return BinderReceiveResult(
        binder=binder_resp,
        intake=BinderIntakeResponse.model_validate(intake),
        is_new_binder=is_new_binder,
    )


@router.post("/mark-ready-bulk", response_model=list[BinderResponse])
def mark_ready_bulk(request: BinderMarkReadyBulkRequest, db: DBSession, user: CurrentUser):
    """Mark all eligible binders for a client as ready for pickup up to a cutoff period."""
    service = BinderService(db)
    binders = service.mark_ready_bulk(
        client_id=request.client_id,
        until_period_year=request.until_period_year,
        until_period_month=request.until_period_month,
        user_id=user.id,
    )
    return [fetch_client_and_build_response(binder, db) for binder in binders]


@router.post("/{binder_id}/ready", response_model=BinderResponse)
def mark_ready_for_pickup(binder_id: int, db: DBSession, user: CurrentUser):
    """Mark binder as ready for pickup."""
    service = BinderService(db)
    binder = service.mark_ready_for_pickup(binder_id=binder_id, user_id=user.id)
    return fetch_client_and_build_response(binder, db)


@router.post("/{binder_id}/return", response_model=BinderResponse)
def return_binder(
    binder_id: int,
    db: DBSession,
    user: CurrentUser,
    request: Optional[BinderReturnRequest] = None,
):
    """Return binder to client."""
    service = BinderService(db)
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
        returned_at=request.returned_at if request else None,
    )
    return fetch_client_and_build_response(binder, db)


@router.post("/{binder_id}/revert-ready", response_model=BinderResponse)
def revert_ready(binder_id: int, db: DBSession, user: CurrentUser):
    """Revert binder from READY_FOR_PICKUP back to IN_OFFICE."""
    service = BinderService(db)
    binder = service.revert_ready(binder_id=binder_id, user_id=user.id)
    return fetch_client_and_build_response(binder, db)


@router.post("/handover", response_model=BinderHandoverResponse, status_code=status.HTTP_201_CREATED)
def create_handover(request: BinderHandoverRequest, db: DBSession, user: CurrentUser):
    """Return multiple binders to a client in a single grouped handover event."""
    service = BinderHandoverService(db)
    handover = service.create_handover(
        client_id=request.client_id,
        binder_ids=request.binder_ids,
        received_by_name=request.received_by_name,
        handed_over_at=request.handed_over_at,
        until_period_year=request.until_period_year,
        until_period_month=request.until_period_month,
        actor_id=user.id,
        notes=request.notes,
    )
    binder_ids = BinderHandoverRepository(db).get_binder_ids_for_handover(handover.id)
    return BinderHandoverResponse(
        id=handover.id,
        client_id=handover.client_id,
        received_by_name=handover.received_by_name,
        handed_over_at=handover.handed_over_at,
        until_period_year=handover.until_period_year,
        until_period_month=handover.until_period_month,
        binder_ids=binder_ids,
        notes=handover.notes,
        created_at=handover.created_at,
    )
