from types import SimpleNamespace

from app.notification.models.notification import NotificationTrigger
from app.notification.services.notification_service import NotificationService


def test_notify_pickup_reminder_delegates_client_notification(test_db):
    service = NotificationService(test_db)
    captured = {}
    service._send_svc = SimpleNamespace(
        _get_client=lambda client_record_id: SimpleNamespace(full_name="Pickup Name"),
        send_client_notification=lambda **kwargs: captured.update(kwargs) or True,
    )
    binder = SimpleNamespace(id=12, binder_number="B-12")

    assert service.notify_pickup_reminder(binder, client_record_id=3, triggered_by=4) is True

    assert captured["trigger"] == NotificationTrigger.PICKUP_REMINDER
    assert captured["binder_id"] == 12
    assert captured["client_record_id"] == 3
    assert captured["triggered_by"] == 4
    assert "B-12" in captured["content"]


def test_notify_annual_report_client_reminder_delegates_client_notification(test_db):
    service = NotificationService(test_db)
    captured = {}
    service._send_svc = SimpleNamespace(
        _get_client=lambda client_record_id: SimpleNamespace(full_name="Annual Name"),
        send_client_notification=lambda **kwargs: captured.update(kwargs) or True,
    )

    assert service.notify_annual_report_client_reminder(
        client_record_id=8,
        annual_report_id=20,
        tax_year=2025,
        triggered_by=6,
    ) is True

    assert captured["trigger"] == NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER
    assert captured["annual_report_id"] == 20
    assert captured["client_record_id"] == 8
    assert captured["triggered_by"] == 6
    assert "2025" in captured["content"]
