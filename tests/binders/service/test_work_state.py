from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import Business, BusinessType
from app.binders.services.work_state_service import WorkState, WorkStateService
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def test_work_state_returned_is_completed():
    """Test COMPLETED state for returned binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-001",
        period_start=date.today() - timedelta(days=30),
        status=BinderStatus.RETURNED,
        created_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.COMPLETED


def test_work_state_ready_is_in_progress():
    """Test IN_PROGRESS state for ready binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-002",
        period_start=date.today() - timedelta(days=20),
        status=BinderStatus.READY_FOR_PICKUP,
        created_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.IN_PROGRESS


def test_work_state_recent_is_in_progress():
    """Test IN_PROGRESS state for recently received binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-003",
        period_start=date.today() - timedelta(days=5),
        status=BinderStatus.IN_OFFICE,
        created_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.IN_PROGRESS


def test_work_state_old_is_waiting():
    """Test WAITING_FOR_WORK state for idle binders."""
    binder = Binder(
        client_id=1,
        binder_number="WS-004",
        period_start=date.today() - timedelta(days=30),
        status=BinderStatus.IN_OFFICE,
        created_by=1,
    )

    state = WorkStateService.derive_work_state(binder)
    assert state == WorkState.WAITING_FOR_WORK


def _persist_client_and_binder(db, user_id: int, received_days_ago: int) -> Binder:
    client = Client(
        full_name="WorkState Client",
        id_number="WS-CL-1",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="WS-010",
        period_start=date.today() - timedelta(days=received_days_ago),
        status=BinderStatus.IN_OFFICE,
        created_by=user_id,
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
    business = Business(
        client_id=binder.client_id,
        business_name="WS Business",
        business_type=BusinessType.COMPANY,
        opened_at=date.today() - timedelta(days=30),
        created_by=test_user.id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)

    repo = NotificationRepository(test_db)
    repo.create(
        business_id=business.id,
        binder_id=binder.id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient="test@example.com",
        content_snapshot="Binder updated",
    )

    assert WorkStateService.is_idle(binder, reference_date=date.today(), db=test_db) is False
