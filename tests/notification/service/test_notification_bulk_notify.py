from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.services.notification_service import NotificationService


def test_bulk_notify_counts_sent_and_failed(monkeypatch, test_db):
    service = NotificationService(test_db)

    outcomes = {1: True, 2: False, 3: True}
    captured = []

    def fake_send_notification(**kwargs):
        captured.append(kwargs)
        return outcomes[kwargs["business_id"]]

    monkeypatch.setattr(service, "send_notification", fake_send_notification)

    result = service.bulk_notify(
        business_ids=[1, 2, 3],
        template="Hello",
        channel=NotificationChannel.WHATSAPP,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        triggered_by=9,
        severity=NotificationSeverity.URGENT,
    )

    assert result == {"sent": 2, "failed": 1}
    assert all(item["preferred_channel"] == "whatsapp" for item in captured)
    assert all(item["severity"] == NotificationSeverity.URGENT for item in captured)
