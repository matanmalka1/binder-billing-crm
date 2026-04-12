from datetime import date

from app.businesses.models.business import Business, EntityType
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def _business(test_db, suffix: str) -> Business:
    client = Client(
        full_name=f"Notif Read Client {suffix}",
        id_number=f"7200000{suffix}",
        email=f"read{suffix}@example.com",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Notif Read Biz {suffix}",
        entity_type=EntityType.OSEK_MURSHE,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def _create(repo: NotificationRepository, business_id: int, msg: str):
    return repo.create(
        business_id=business_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="x@example.com",
        content_snapshot=msg,
    )


def test_notification_repository_mark_all_read_without_scope(test_db):
    repo = NotificationRepository(test_db)
    b1 = _business(test_db, "1")
    b2 = _business(test_db, "2")

    _create(repo, b1.id, "a")
    _create(repo, b2.id, "b")

    assert repo.count_unread() == 2
    updated_all = repo.mark_all_read()
    assert updated_all == 2
    assert repo.count_unread() == 0
