from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.services.work_state_service import WorkState, WorkStateService
from app.clients.models.client import Client, ClientType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


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


def _persist_client_and_binder(db, user_id: int, received_days_ago: int) -> Binder:
    client = Client(
        full_name="WorkState Client",
        id_number="WS-CL-1",
        client_type=ClientType.COMPANY,
        opened_at=date.today() - timedelta(days=60),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="WS-010",
        binder_type=BinderType.VAT,
        received_at=date.today() - timedelta(days=received_days_ago),
        status=BinderStatus.IN_OFFICE,
        received_by=user_id,
    )
    db.add(binder)
    db.commit()
    db.refresh(binder)
    return binder


def test_is_idle_true_without_recent_activity(test_db, test_user):
    binder = _persist_client_and_binder(test_db, test_user.id, received_days_ago=40)

    assert WorkStateService.is_idle(binder, reference_date=date.today(), db=test_db) is True


def test_is_idle_false_when_recent_notification_exists(test_db, test_user):
    binder = _persist_client_and_binder(test_db, test_user.id, received_days_ago=40)
    repo = NotificationRepository(test_db)
    repo.create(
        client_id=binder.client_id,
        binder_id=binder.id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient="test@example.com",
        content_snapshot="Binder updated",
    )

    assert WorkStateService.is_idle(binder, reference_date=date.today(), db=test_db) is False
