from datetime import date

from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.clients.models.client import Client, ClientType


def _client(test_db):
    client = Client(
        full_name="Notif Client",
        id_number="NTF001",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_notification_repository_lifecycle(test_db):
    repo = NotificationRepository(test_db)
    client = _client(test_db)

    pending = repo.create(
        client_id=client.id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient="client@example.com",
        content_snapshot="Binder received",
    )
    later = repo.create(
        client_id=client.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.WHATSAPP,
        recipient="client@example.com",
        content_snapshot="Pay now",
    )

    sent = repo.mark_sent(pending.id)
    assert sent.status == NotificationStatus.SENT
    assert sent.sent_at is not None

    failed = repo.mark_failed(later.id, error_message="delivery error")
    assert failed.status == NotificationStatus.FAILED
    assert failed.failed_at is not None
    assert failed.error_message == "delivery error"

    ordered = repo.list_by_client(client_id=client.id)
    assert [n.id for n in ordered] == [later.id, pending.id]
    assert repo.count_by_client(client_id=client.id) == 2

    assert repo.mark_sent(notification_id=9999) is None
