from datetime import date
from typing import Optional

from app.actions.action_contracts import get_binder_actions
from app.binders.schemas.binder import BinderResponse
from app.binders.services.signals_service import SignalsService
from app.binders.services.work_state_service import WorkStateService
from app.users.api.deps import DBSession


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
