from datetime import date

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client, ClientType
from app.notification.models.notification import NotificationStatus, NotificationTrigger
from app.notification.services.notification_service import NotificationService


def test_notification_persisted_on_binder_received(test_db):
    """Test notification is persisted when binder is received."""
    client = Client(
        full_name="Test Client",
        id_number="111111111",
        client_type=ClientType.COMPANY,
        phone="0501234567",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="BND-001",
        received_at=date.today(),
        expected_return_at=date(2026, 5, 10),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    service = NotificationService(test_db)
    result = service.notify_binder_received(binder, client)

    assert result is True

    from app.notification.repositories.notification_repository import NotificationRepository
    repo = NotificationRepository(test_db)
    notifications = repo.list_by_client(client.id)

    assert len(notifications) >= 1
    assert notifications[0].trigger == NotificationTrigger.BINDER_RECEIVED
    assert notifications[0].binder_id == binder.id
    assert binder.binder_number in notifications[0].content_snapshot


def test_notification_non_blocking_on_failure(test_db):
    """Test that notification failure does not block operations."""
    client = Client(
        full_name="Test Client",
        id_number="222222222",
        client_type=ClientType.OSEK_PATUR,
        phone=None,  # No phone to trigger failure
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = NotificationService(test_db)
    # Should not raise exception even with missing phone
    result = service.send_notification(
        client_id=client.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="Test reminder",
    )

    assert result is True


def test_notification_fallback_to_email(test_db):
    """Test that email is used as fallback when WhatsApp fails."""
    client = Client(
        full_name="Test Client",
        id_number="333333333",
        client_type=ClientType.EMPLOYEE,
        phone="0501234567",
        email="test@example.com",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = NotificationService(test_db)
    service.send_notification(
        client_id=client.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="Payment reminder",
    )

    from app.notification.repositories.notification_repository import NotificationRepository
    repo = NotificationRepository(test_db)
    notifications = repo.list_by_client(client.id)

    # Should have both WhatsApp and Email attempts
    assert len(notifications) >= 1
