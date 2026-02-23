from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.binders.api.binders_common import to_binder_response
from app.binders.schemas.binder import BinderListResponse, BinderResponse
from app.binders.services.binder_service import BinderService
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService
from app.clients.repositories.client_repository import ClientRepository
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = None,
    work_state: Optional[str] = None,
):
    """List active binders with optional filters."""
    service = BinderService(db)
    signals_service = SignalsService(db)
    reference_date = date.today()

    binders = service.list_active_binders(client_id=client_id, status=status_filter)

    client_repo = ClientRepository(db)
    client_ids = list({b.client_id for b in binders})
    clients = client_repo.list_by_ids(client_ids)
    client_name_map: dict[int, str] = {c.id: c.full_name for c in clients}

    items = []
    for binder in binders:
        current_work_state = WorkStateService.derive_work_state(binder, reference_date, db).value
        current_signals = signals_service.compute_binder_signals(binder, reference_date)

        if work_state and current_work_state != work_state:
            continue

        items.append(
            to_binder_response(
                binder=binder,
                db=db,
                signals_service=signals_service,
                reference_date=reference_date,
                work_state=current_work_state,
                signals=current_signals,
                client_name=client_name_map.get(binder.client_id),
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

    client_repo = ClientRepository(db)
    client = client_repo.get_by_id(binder.client_id)

    return to_binder_response(
        binder=binder,
        db=db,
        signals_service=signals_service,
        reference_date=date.today(),
        client_name=client.full_name if client else None,
    )
