from datetime import date
from types import SimpleNamespace

from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.services.notification_service import NotificationService


def test_notification_persisted_on_binder_received(test_db):
    service = NotificationService(test_db)
    created = {}

    service.notification_repo = SimpleNamespace(
        create=lambda **kwargs: created.setdefault("payload", kwargs) or SimpleNamespace(id=100),
        mark_sent=lambda _id: None,
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="Acme Biz"),
        SimpleNamespace(phone=None, email="biz@example.com"),
    )
    service.email = SimpleNamespace(send=lambda *_args, **_kwargs: (True, None))
    service.whatsapp = SimpleNamespace(enabled=False, send=lambda *_args, **_kwargs: (False, "off"))

    binder = SimpleNamespace(id=11, binder_number="BND-001", received_at=date(2026, 3, 1))
    business = SimpleNamespace(id=1, business_name="Acme Biz")

    assert service.notify_binder_received(binder, business) is True
    assert created["payload"]["business_id"] == 1
    assert created["payload"]["binder_id"] == 11
    assert created["payload"]["trigger"] == NotificationTrigger.BINDER_RECEIVED
    assert "BND-001" in created["payload"]["content_snapshot"]


def test_notification_non_blocking_on_failure(test_db):
    service = NotificationService(test_db)
    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="A"),
        SimpleNamespace(phone=None, email="a@example.com"),
    )
    service.notification_repo = SimpleNamespace(
        create=lambda **_kwargs: SimpleNamespace(id=55),
        mark_sent=lambda *_args, **_kwargs: None,
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service.email = SimpleNamespace(send=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("smtp exploded")))
    service.whatsapp = SimpleNamespace(enabled=False, send=lambda *_args, **_kwargs: (False, "off"))

    result = service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="Test reminder",
    )

    assert result is True


def test_notification_fallback_to_email(test_db):
    service = NotificationService(test_db)
    calls = {"email": 0}
    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="Fallback Biz"),
        SimpleNamespace(phone="0501234567", email="test@example.com"),
    )
    service.notification_repo = SimpleNamespace(
        create=lambda **_kwargs: SimpleNamespace(id=12),
        mark_sent=lambda *_args, **_kwargs: None,
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service.whatsapp = SimpleNamespace(enabled=True, send=lambda *_args, **_kwargs: (False, "wa failed"))
    service.email = SimpleNamespace(
        send=lambda *_args, **_kwargs: (calls.__setitem__("email", calls["email"] + 1) or True, None)
    )

    service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="Payment reminder",
        preferred_channel="whatsapp",
    )

    assert calls["email"] == 1


def test_notify_payment_reminder_delegates_trigger(test_db):
    service = NotificationService(test_db)
    seen = {}

    def _fake_send_notification(**kwargs):
        seen.update(kwargs)
        return True

    service.send_notification = _fake_send_notification

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

    service.send_notification = _fake_send_notification
    binder = SimpleNamespace(id=3, binder_number="BN-3")
    business = SimpleNamespace(id=9, business_name="Pickup Biz")

    assert service.notify_ready_for_pickup(binder, business) is True
    assert captured["business_id"] == 9
    assert captured["binder_id"] == 3
    assert captured["trigger"] == NotificationTrigger.BINDER_READY_FOR_PICKUP


def test_send_notification_whatsapp_success_marks_sent(test_db):
    service = NotificationService(test_db)
    marks = {"sent": 0}

    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="C"),
        SimpleNamespace(phone="050", email="a@a.com"),
    )
    service.notification_repo = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(id=55, channel=kwargs["channel"]),
        mark_sent=lambda _id: marks.__setitem__("sent", marks["sent"] + 1),
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service.whatsapp = SimpleNamespace(enabled=True, send=lambda phone, content: (True, None))

    assert service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        content="hello",
        preferred_channel="whatsapp",
    ) is True
    assert marks["sent"] == 1


def test_send_notification_email_failure_marks_failed(test_db):
    service = NotificationService(test_db)
    marks = {"failed": 0}
    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="C"),
        SimpleNamespace(phone=None, email="a@a.com"),
    )
    service.notification_repo = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(id=777, channel=kwargs["channel"]),
        mark_sent=lambda *_args, **_kwargs: None,
        mark_failed=lambda _id, _err: marks.__setitem__("failed", marks["failed"] + 1),
    )
    service.email = SimpleNamespace(send=lambda *_args, **_kwargs: (False, "smtp-failed"))
    service.whatsapp = SimpleNamespace(enabled=False, send=lambda *_args, **_kwargs: (False, "no"))

    assert service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True
    assert marks["failed"] == 1


def test_send_notification_business_missing_or_email_missing_returns_true(test_db):
    service = NotificationService(test_db)
    service._get_business_and_client = lambda _id: None

    assert service.send_notification(
        business_id=999,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True

    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="NoEmail"),
        SimpleNamespace(phone=None, email=None),
    )
    assert service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
    ) is True


def test_send_notification_passes_severity_to_repository(test_db):
    service = NotificationService(test_db)
    captured = {}

    service._get_business_and_client = lambda _id: (
        SimpleNamespace(id=1, business_name="Severity Biz"),
        SimpleNamespace(phone=None, email="s@example.com"),
    )

    def _create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=88)

    service.notification_repo = SimpleNamespace(
        create=_create,
        mark_sent=lambda *_args, **_kwargs: None,
        mark_failed=lambda *_args, **_kwargs: None,
    )
    service.email = SimpleNamespace(send=lambda *_args, **_kwargs: (True, None))

    assert service.send_notification(
        business_id=1,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        content="x",
        severity=NotificationSeverity.CRITICAL,
    ) is True

    assert captured["channel"] == NotificationChannel.EMAIL
    assert captured["severity"] == NotificationSeverity.CRITICAL


def test_list_and_read_delegation_methods(test_db):
    service = NotificationService(test_db)
    service.notification_repo = SimpleNamespace(
        list_paginated=lambda **kwargs: (["n1"], 1),
        list_recent=lambda **kwargs: ["n2"],
        count_unread=lambda **kwargs: 3,
        mark_read=lambda ids: len(ids),
        mark_all_read=lambda business_id=None: 5,
    )

    assert service.list_paginated(page=2, page_size=10, business_id=4) == (["n1"], 1)
    assert service.list_recent(limit=5, business_id=4) == ["n2"]
    assert service.count_unread(business_id=4) == 3
    assert service.mark_read([1, 2]) == 2
    assert service.mark_all_read(business_id=4) == 5


def test_resolve_recipient_name_fallbacks(test_db):
    service = NotificationService(test_db)

    named = SimpleNamespace(id=1, business_name="Biz Name", client=None)
    assert service._resolve_recipient_name(named) == "Biz Name"

    with_client = SimpleNamespace(id=2, business_name=None, client=SimpleNamespace(full_name="Owner Name"))
    assert service._resolve_recipient_name(with_client) == "Owner Name"

    service._get_business_and_client = lambda _id: (SimpleNamespace(id=3), SimpleNamespace(full_name="Joined Name"))
    no_rel = SimpleNamespace(id=3, business_name=None, client=None)
    assert service._resolve_recipient_name(no_rel) == "Joined Name"

    service._get_business_and_client = lambda _id: None
    unknown = SimpleNamespace(id=4, business_name=None, client=None)
    assert service._resolve_recipient_name(unknown) == "לקוח"
