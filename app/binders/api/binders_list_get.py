from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.binders.api.binders_common import fetch_client_and_build_response, to_binder_response
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


_ALLOWED_SORT_COLS = {"received_at", "days_in_office", "status", "client_name"}


@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = None,
    work_state: Optional[str] = None,
    query: Optional[str] = None,
    client_name: Optional[str] = None,
    binder_number: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
):
    """List active binders with optional filters, sorting, and pagination."""
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    effective_sort_by = sort_by if sort_by in _ALLOWED_SORT_COLS else "received_at"

    # client_name sort is handled post-fetch (name not in DB)
    db_sort_by = effective_sort_by if effective_sort_by != "client_name" else "received_at"

    service = BinderService(db)
    signals_service = SignalsService(db)
    reference_date = date.today()

    # Fetch all matching binders; work_state & text filters applied in Python
    binders = service.list_active_binders(
        client_id=client_id,
        status=status_filter,
        sort_by=db_sort_by,
        sort_dir=sort_dir,
    )

    client_repo = ClientRepository(db)
    client_ids = list({b.client_id for b in binders})
    clients = client_repo.list_by_ids(client_ids)
    client_name_map: dict[int, str] = {c.id: c.full_name for c in clients}

    items: list[BinderResponse] = []
    for binder in binders:
        current_work_state = WorkStateService.derive_work_state(binder, reference_date, db).value
        current_signals = signals_service.compute_binder_signals(binder, reference_date)

        if work_state and current_work_state != work_state:
            continue

        c_name = client_name_map.get(binder.client_id)

        if query:
            q = query.lower()
            name_match = c_name and q in c_name.lower()
            number_match = q in binder.binder_number.lower()
            if not name_match and not number_match:
                continue

        if client_name and (not c_name or client_name.lower() not in c_name.lower()):
            continue

        if binder_number and binder_number.lower() not in binder.binder_number.lower():
            continue

        items.append(
            to_binder_response(
                binder=binder,
                db=db,
                signals_service=signals_service,
                reference_date=reference_date,
                work_state=current_work_state,
                signals=current_signals,
                client_name=c_name,
            )
        )

    if effective_sort_by == "client_name":
        items.sort(
            key=lambda r: (r.client_name or "").lower(),
            reverse=(sort_dir == "desc"),
        )

    total = len(items)
    offset = (page - 1) * page_size
    page_items = items[offset: offset + page_size]

    return BinderListResponse(items=page_items, page=page, page_size=page_size, total=total)


@router.get("/{binder_id}", response_model=BinderResponse)
def get_binder(binder_id: int, db: DBSession, user: CurrentUser):
    """Get binder by ID."""
    service = BinderService(db)
    signals_service = SignalsService(db)
    binder = service.get_binder(binder_id)

    if not binder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Binder not found")

    return fetch_client_and_build_response(binder, db, signals_service)
