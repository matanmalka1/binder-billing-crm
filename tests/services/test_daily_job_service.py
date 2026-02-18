from datetime import date, timedelta

from app.models import Binder, BinderStatus, Client, ClientType
from app.binders.services.daily_sla_job_service import DailySLAJobService
from app.repositories import NotificationRepository
from app.models import NotificationTrigger


def test_daily_job_scans_active_binders(test_db, test_user):
    """Test that daily job scans all active binders."""
    client = Client(
        full_name="Job Test Client",
        id_number="444444444",
        client_type=ClientType.COMPANY,
        phone="0501234567",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    # Create multiple binders
    binder1 = Binder(
        client_id=client.id,
        binder_number="BND-JOB-1",
        received_at=date.today() - timedelta(days=80),
        expected_return_at=date.today() - timedelta(days=5),  # Overdue
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    binder2 = Binder(
        client_id=client.id,
        binder_number="BND-JOB-2",
        received_at=date.today() - timedelta(days=76),
        expected_return_at=date.today() + timedelta(days=14),  # Approaching
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    binder3 = Binder(
        client_id=client.id,
        binder_number="BND-JOB-3",
        received_at=date.today() - timedelta(days=5),
        expected_return_at=date.today() + timedelta(days=60),
        status=BinderStatus.READY_FOR_PICKUP,
        received_by=test_user.id,
    )
    test_db.add_all([binder1, binder2, binder3])
    test_db.commit()

    service = DailySLAJobService(test_db)
    result = service.run(reference_date=date.today())

    assert result["binders_scanned"] == 3
    assert result["overdue_notifications"] >= 1
    assert result["approaching_sla_notifications"] >= 1
    assert result["ready_for_pickup_notifications"] >= 1

    repo = NotificationRepository(test_db)
    notifications = repo.list_by_client(client.id, page_size=50)
    triggers = {n.trigger for n in notifications}
    assert NotificationTrigger.BINDER_OVERDUE in triggers
    assert NotificationTrigger.BINDER_APPROACHING_SLA in triggers
    assert NotificationTrigger.BINDER_READY_FOR_PICKUP in triggers


def test_daily_job_idempotency(test_db, test_user):
    """Test that running job multiple times does not duplicate notifications."""
    client = Client(
        full_name="Idempotent Test Client",
        id_number="555555555",
        client_type=ClientType.OSEK_MURSHE,
        phone="0501234567",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="BND-IDEM-1",
        received_at=date.today() - timedelta(days=100),
        expected_return_at=date.today() - timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    service = DailySLAJobService(test_db)
    repo = NotificationRepository(test_db)
    
    # Run job twice
    result1 = service.run(reference_date=date.today())
    count_after_first = repo.count_by_client(client.id)
    result2 = service.run(reference_date=date.today())
    count_after_second = repo.count_by_client(client.id)

    assert result1["overdue_notifications"] == 1
    assert result2["overdue_notifications"] == 0
    assert count_after_first == count_after_second
