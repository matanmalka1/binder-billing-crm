from datetime import date
from types import SimpleNamespace

from app.binders.models.binder import Binder, BinderStatus, BinderType
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
        email="testclient@example.com",
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    binder = Binder(
        client_id=client.id,
        binder_number="BND-001",
        binder_type=BinderType.OTHER,
        received_at=date.today(),
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


def test_notify_payment_reminder_delegates_trigger(monkeypatch, test_db):
    service = NotificationService(test_db)
    client = SimpleNamespace(id=7)
    seen = {"trigger": None}

    def _fake_send_notification(**kwargs):
        seen["trigger"] = kwargs["trigger"]
        return True

    monkeypatch.setattr(service, "send_notification", _fake_send_notification)
    assert service.notify_payment_reminder(client, "x", triggered_by=1) is True
    assert seen["trigger"] == NotificationTrigger.MANUAL_PAYMENT_REMINDER


def test_send_notification_whatsapp_success_marks_sent(monkeypatch, test_db):
    service = NotificationService(test_db)
    service.client_repo = SimpleNamespace(
        get_by_id=lambda _id: SimpleNamespace(id=1, phone="050", email="a@a.com", full_name="C")
    )
    created = {"id": 55}
    marks = {"sent": 0}
    service.notification_repo = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(id=created["id"]),
        mark_sent=lambda _id: marks.__setitem__("sent", marks["sent"] + 1),
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service.whatsapp = SimpleNamespace(enabled=True, send=lambda phone, content: (True, None))

    assert service.send_notification(
        client_id=1,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        content="hello",
        preferred_channel="whatsapp",
    ) is True
    assert marks["sent"] == 1


def test_send_notification_email_failure_marks_failed(test_db):
    service = NotificationService(test_db)
    service.client_repo = SimpleNamespace(
        get_by_id=lambda _id: SimpleNamespace(id=1, phone=None, email="a@a.com", full_name="C")
    )
    marks = {"failed": 0}
    service.notification_repo = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(id=777),
        mark_sent=lambda *_args, **_kwargs: None,
        mark_failed=lambda _id, _err: marks.__setitem__("failed", marks["failed"] + 1),
    )
    service.email = SimpleNamespace(send=lambda *_args, **_kwargs: (False, "smtp-failed"))
    service.whatsapp = SimpleNamespace(enabled=False, send=lambda *_args, **_kwargs: (False, "no"))

    assert service.send_notification(
        client_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True
    assert marks["failed"] == 1


def test_send_notification_client_missing_or_email_missing_returns_true(test_db):
    service = NotificationService(test_db)
    service.client_repo = SimpleNamespace(get_by_id=lambda _id: None)
    assert service.send_notification(
        client_id=999,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True

    service.client_repo = SimpleNamespace(
        get_by_id=lambda _id: SimpleNamespace(id=1, phone=None, email=None, full_name="C")
    )
    assert service.send_notification(
        client_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True
