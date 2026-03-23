from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.services.notification_service import NotificationService


def test_bulk_notify_counts_sent_and_failed(monkeypatch, test_db):
    service = NotificationService(test_db)

    captured = {}
    monkeypatch.setattr(
        service,
        "_send_svc",
        type(
            "_SendSvc",
            (),
            {
                "bulk_notify": staticmethod(lambda **kwargs: captured.update(kwargs) or {"sent": 2, "failed": 1}),
            },
        )(),
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
    assert captured["channel"] == NotificationChannel.WHATSAPP
    assert captured["severity"] == NotificationSeverity.URGENT
