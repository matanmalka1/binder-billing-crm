from datetime import datetime, UTC
from types import SimpleNamespace

from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.services.notification_service import NotificationService


def test_notify_payment_reminder_delegates_trigger(test_db):
    service = NotificationService(test_db)
    seen = {}

    def _fake_send_notification(**kwargs):
        seen.update(kwargs)
        return True

    service._send_svc = SimpleNamespace(send_notification=_fake_send_notification)

    assert service.notify_payment_reminder(7, "x", triggered_by=1) is True
    assert seen["business_id"] == 7
    assert seen["trigger"] == NotificationTrigger.MANUAL_PAYMENT_REMINDER
    assert seen["triggered_by"] == 1


def test_notify_ready_for_pickup_delegates_to_send_notification(test_db):
    service = NotificationService(test_db)
    captured = {}

    def _fake_send_notification(**kwargs):
        captured.update(kwargs)
        return True

    fake_person = SimpleNamespace(full_name="Pickup Client")
    service._send_svc = SimpleNamespace(
        _get_client=lambda cr_id: fake_person,
        send_client_notification=_fake_send_notification,
    )
    binder = SimpleNamespace(id=3, binder_number="BN-3")

    assert service.notify_ready_for_pickup(binder, 9) is True
    assert captured["client_record_id"] == 9
    assert captured["binder_id"] == 3
    assert captured["trigger"] == NotificationTrigger.BINDER_READY_FOR_PICKUP


def test_notify_binder_received_delegates_to_send_notification(test_db):
    service = NotificationService(test_db)
    captured = {}

    def _fake_send_notification(**kwargs):
        captured.update(kwargs)
        return True

    fake_person = SimpleNamespace(full_name="Acme Client")
    service._send_svc = SimpleNamespace(
        _get_client=lambda cr_id: fake_person,
        send_client_notification=_fake_send_notification,
    )
    binder = SimpleNamespace(id=11, binder_number="BND-001", period_start="2026-03")

    assert service.notify_binder_received(binder, 1) is True
    assert captured["client_record_id"] == 1
    assert captured["binder_id"] == 11
    assert captured["trigger"] == NotificationTrigger.BINDER_RECEIVED
    assert "BND-001" in captured["content"]


def test_send_notification_delegates_to_send_service(test_db):
    service = NotificationService(test_db)
    captured = {}

    service._send_svc = SimpleNamespace(
        send_notification=lambda **kwargs: captured.update(kwargs) or True,
    )

    assert service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
        severity=NotificationSeverity.CRITICAL,
        preferred_channel="whatsapp",
    ) is True

    assert captured["business_id"] == 1
    assert captured["trigger"] == NotificationTrigger.MANUAL_PAYMENT_REMINDER
    assert captured["severity"] == NotificationSeverity.CRITICAL
    assert captured["preferred_channel"] == "whatsapp"


def test_bulk_notify_delegates_to_send_service(test_db):
    service = NotificationService(test_db)
    seen = {}

    service._send_svc = SimpleNamespace(
        bulk_notify=lambda **kwargs: seen.update(kwargs) or {"sent": 2, "failed": 1},
    )

    result = service.bulk_notify(
        business_ids=[1, 2, 3],
        template="Hello",
        channel=NotificationChannel.WHATSAPP,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        triggered_by=9,
        severity=NotificationSeverity.URGENT,
    )

    assert result == {"sent": 2, "failed": 1}
    assert seen["business_ids"] == [1, 2, 3]
    assert seen["channel"] == NotificationChannel.WHATSAPP
    assert seen["severity"] == NotificationSeverity.URGENT


def test_list_and_read_delegation_methods(test_db):
    service = NotificationService(test_db)
    n1 = SimpleNamespace(
        id=1,
        client_id=8,
        business_id=4,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="a@x.com",
        content_snapshot="x",
        severity=NotificationSeverity.INFO,
        status=NotificationStatus.PENDING,
        sent_at=None,
        failed_at=None,
        error_message=None,
        retry_count=0,
        is_read=False,
        read_at=None,
        read_by=None,
        triggered_by=None,
        created_at=datetime.now(UTC),
    )
    n2 = SimpleNamespace(**{**n1.__dict__, "id": 2})

    service.notification_repo = SimpleNamespace(
        list_paginated=lambda **kwargs: ([n1], 1),
        list_recent=lambda **kwargs: [n2],
        count_unread=lambda **kwargs: 3,
        mark_read=lambda ids: len(ids),
        mark_all_read=lambda **kwargs: 5,
    )
    service.business_repo = SimpleNamespace(
        list_by_ids=lambda ids: [SimpleNamespace(id=4, full_name="Biz 4")],
    )

    items, total = service.list_paginated(page=2, page_size=10, business_id=4)
    assert total == 1
    assert items[0].business_name == "Biz 4"

    recent = service.list_recent(limit=5, business_id=4)
    assert len(recent) == 1
    assert recent[0].business_name == "Biz 4"

    assert service.count_unread(business_id=4) == 3
    assert service.mark_read([1, 2]) == 2
    assert service.mark_all_read(business_id=4) == 5
