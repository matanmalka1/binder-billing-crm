from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.schemas import BinderListResponse, BinderReceiveRequest, BinderResponse, BinderReturnRequest
from app.services import BinderService, SLAService, SignalsService, WorkStateService
from app.services.action_contracts import get_binder_actions

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


def _to_binder_response(
    binder,
    db: DBSession,
    signals_service: SignalsService,
    reference_date: date,
    work_state: Optional[str] = None,
    sla_state: Optional[str] = None,
    signals: Optional[list[str]] = None,
) -> BinderResponse:
    response = BinderResponse.model_validate(binder)
    response.days_in_office = (reference_date - binder.received_at).days
    response.work_state = work_state or WorkStateService.derive_work_state(
        binder,
        reference_date,
        db,
    ).value
    response.sla_state = sla_state or SLAService.derive_sla_state(binder, reference_date)
    response.signals = signals if signals is not None else signals_service.compute_binder_signals(
        binder,
        reference_date,
    )
    response.available_actions = get_binder_actions(binder)
    return response


@router.post("/receive", response_model=BinderResponse, status_code=status.HTTP_201_CREATED)
def receive_binder(request: BinderReceiveRequest, db: DBSession, user: CurrentUser):
    """Receive new binder (intake flow)."""
    service = BinderService(db)
    signals_service = SignalsService(db)

    try:
        binder = service.receive_binder(
            client_id=request.client_id,
            binder_number=request.binder_number,
            received_at=request.received_at,
            received_by=request.received_by,
            notes=request.notes,
        )

        return _to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
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
        return _to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
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
        return _to_binder_response(
            binder=binder,
            db=db,
            signals_service=signals_service,
            reference_date=date.today(),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = None,
    work_state: Optional[str] = None,
    sla_state: Optional[str] = None,
):
    """List active binders with optional filters."""
    service = BinderService(db)
    signals_service = SignalsService(db)
    reference_date = date.today()

    binders = service.list_active_binders(client_id=client_id, status=status_filter)

    items = []
    for binder in binders:
        current_work_state = WorkStateService.derive_work_state(
            binder,
            reference_date,
            db,
        ).value
        current_sla_state = SLAService.derive_sla_state(binder, reference_date)
        current_signals = signals_service.compute_binder_signals(binder, reference_date)

        if work_state and current_work_state != work_state:
            continue
        if sla_state and current_sla_state != sla_state:
            continue

        items.append(
            _to_binder_response(
                binder=binder,
                db=db,
                signals_service=signals_service,
                reference_date=reference_date,
                work_state=current_work_state,
                sla_state=current_sla_state,
                signals=current_signals,
            )
        )

    return BinderListResponse(items=items)


@router.get("/{binder_id}", response_model=BinderResponse)
def get_binder(binder_id: int, db: DBSession, user: CurrentUser):
    """Get binder by ID."""
    service = BinderService(db)
    signals_service = SignalsService(db)
    binder = service.get_binder(binder_id)

    if not binder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binder not found")

    return _to_binder_response(
        binder=binder,
        db=db,
        signals_service=signals_service,
        reference_date=date.today(),
    )
