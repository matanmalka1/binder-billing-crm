from datetime import date
from typing import Optional

from app.actions.action_contracts import get_binder_actions
from app.binders.schemas.binder import BinderResponse
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService
from app.clients.repositories.client_repository import ClientRepository
from app.users.api.deps import DBSession


def fetch_client_and_build_response(binder, db: DBSession, signals_service: SignalsService) -> BinderResponse:
    """Fetch the binder's client by ID and build the full BinderResponse."""
    client = ClientRepository(db).get_by_id(binder.client_id)
    return to_binder_response(
        binder=binder,
        db=db,
        signals_service=signals_service,
        reference_date=date.today(),
        client_name=client.full_name if client else None,
    )


def to_binder_response(
    binder,
    db: DBSession,
    signals_service: SignalsService,
    reference_date: date,
    work_state: Optional[str] = None,
    signals: Optional[list[str]] = None,
    client_name: Optional[str] = None,
) -> BinderResponse:
    response = BinderResponse.model_validate(binder)
    response.days_in_office = (reference_date - binder.received_at).days
    response.work_state = work_state or WorkStateService.derive_work_state(
        binder,
        reference_date,
        db,
    ).value
    response.signals = signals if signals is not None else signals_service.compute_binder_signals(
        binder,
        reference_date,
    )
    response.available_actions = get_binder_actions(binder)
    response.client_name = client_name
    return response
