from datetime import date

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.binder_helpers import validate_ready_transition, validate_return_transition


def _binder(status: BinderStatus) -> Binder:
    return Binder(
        client_id=1,
        binder_number="BDR-HELPER-1",
        period_start=date.today(),
        created_by=1,
        status=status,
    )


def test_validate_ready_transition_allows_in_office():
    validate_ready_transition(_binder(BinderStatus.IN_OFFICE))


def test_validate_ready_transition_rejects_wrong_status():
    with pytest.raises(Exception) as exc:
        validate_ready_transition(_binder(BinderStatus.RETURNED))
    assert getattr(exc.value, "code", None) == "BINDER.INVALID_STATUS"


def test_validate_return_transition_requires_pickup_person():
    with pytest.raises(Exception) as exc:
        validate_return_transition(_binder(BinderStatus.READY_FOR_PICKUP), "")
    assert getattr(exc.value, "code", None) == "BINDER.MISSING_PICKUP_PERSON"


def test_validate_return_transition_requires_ready_for_pickup_status():
    with pytest.raises(Exception) as exc:
        validate_return_transition(_binder(BinderStatus.IN_OFFICE), "John")
    assert getattr(exc.value, "code", None) == "BINDER.INVALID_STATUS"


def test_validate_return_transition_allows_valid_state_and_pickup():
    validate_return_transition(_binder(BinderStatus.READY_FOR_PICKUP), "John Doe")
