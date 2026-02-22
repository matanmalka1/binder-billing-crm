from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.binders.services.work_state_service import WorkState, WorkStateService


def test_work_state_returned_is_completed():
    """Test COMPLETED state for returned binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-001",
        received_at=date.today() - timedelta(days=30),
        status=BinderStatus.RETURNED,
        received_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.COMPLETED


def test_work_state_ready_is_in_progress():
    """Test IN_PROGRESS state for ready binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-002",
        received_at=date.today() - timedelta(days=20),
        status=BinderStatus.READY_FOR_PICKUP,
        received_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.IN_PROGRESS


def test_work_state_recent_is_in_progress():
    """Test IN_PROGRESS state for recently received binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-003",
        received_at=date.today() - timedelta(days=5),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.IN_PROGRESS


def test_work_state_old_is_waiting():
    """Test WAITING_FOR_WORK state for idle binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-004",
        received_at=date.today() - timedelta(days=30),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.WAITING_FOR_WORK
