from app.notification.services.notification_service import NotificationService


def test_bulk_notify_counts_sent_and_failed(monkeypatch, test_db):
    service = NotificationService(test_db)

    outcomes = {1: True, 2: False, 3: True}

    def fake_send_notification(*, client_id, **kwargs):
        return outcomes[client_id]

    monkeypatch.setattr(service, "send_notification", fake_send_notification)

    result = service.bulk_notify(client_ids=[1, 2, 3], template="Hello")

    assert result == {"sent": 2, "failed": 1}
