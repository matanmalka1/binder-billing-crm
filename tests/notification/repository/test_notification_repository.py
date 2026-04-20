from datetime import date

from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository


def _business(test_db, suffix: str) -> Business:
    client = Client(
        full_name=f"Notif Repo Client {suffix}",
        id_number=f"7100000{suffix}",
        email=f"repo{suffix}@example.com",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Notif Repo Biz {suffix}",
        opened_at=date(2024, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_notification_repository_lifecycle(test_db):
    repo = NotificationRepository(test_db)
    business = _business(test_db, "1")

    pending = repo.create(
        client_id=business.client_id,
        business_id=business.id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient="client@example.com",
        content_snapshot="Binder received",
        triggered_by=123,
        severity=NotificationSeverity.WARNING,
    )
    later = repo.create(
        client_id=business.client_id,
        business_id=business.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.WHATSAPP,
        recipient="0501111111",
        content_snapshot="Pay now",
    )

    assert pending.triggered_by == 123
    assert pending.severity == NotificationSeverity.WARNING

    sent = repo.mark_sent(pending.id)
    assert sent.status == NotificationStatus.SENT
    assert sent.sent_at is not None

    failed = repo.mark_failed(later.id, error_message="delivery error")
    assert failed.status == NotificationStatus.FAILED
    assert failed.failed_at is not None
    assert failed.error_message == "delivery error"

    ordered = repo.list_by_business(business_id=business.id)
    assert [n.id for n in ordered] == [later.id, pending.id]
    assert repo.count_by_business(business_id=business.id) == 2

    assert repo.get_by_id(pending.id) is not None
    assert repo.mark_sent(notification_id=9999) is None
    assert repo.mark_failed(notification_id=9999, error_message="x") is None


def test_notification_repository_read_and_recent_and_pagination(test_db):
    repo = NotificationRepository(test_db)
    b1 = _business(test_db, "2")
    b2 = _business(test_db, "3")

    n1 = repo.create(
        client_id=b1.client_id,
        business_id=b1.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="a@example.com",
        content_snapshot="a",
    )
    n2 = repo.create(
        client_id=b1.client_id,
        business_id=b1.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="a@example.com",
        content_snapshot="b",
    )
    n3 = repo.create(
        client_id=b2.client_id,
        business_id=b2.id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="b@example.com",
        content_snapshot="c",
    )

    assert repo.count_unread(business_id=b1.id) == 2

    updated = repo.mark_read([n1.id])
    assert updated == 1
    assert repo.count_unread(business_id=b1.id) == 1

    updated_all = repo.mark_all_read(business_id=b1.id)
    assert updated_all == 1
    assert repo.count_unread(business_id=b1.id) == 0
    assert repo.count_unread() == 1

    recent_b2 = repo.list_recent(limit=10, business_id=b2.id)
    assert [n.id for n in recent_b2] == [n3.id]

    items, total = repo.list_paginated(page=1, page_size=1, business_id=b1.id)
    assert total == 2
    assert len(items) == 1
    assert items[0].id == n2.id

    global_items, global_total = repo.list_paginated(page=1, page_size=10)
    assert global_total == 3
    assert len(global_items) == 3


def test_notification_repository_exists_for_binder_trigger(test_db):
    repo = NotificationRepository(test_db)
    business = _business(test_db, "4")

    assert repo.exists_for_binder_trigger(binder_id=77, trigger=NotificationTrigger.BINDER_RECEIVED) is False

    repo.create(
        client_id=business.client_id,
        business_id=business.id,
        binder_id=77,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient="client@example.com",
        content_snapshot="binder received",
    )

    assert repo.exists_for_binder_trigger(binder_id=77, trigger=NotificationTrigger.BINDER_RECEIVED) is True
    assert repo.exists_for_binder_trigger(binder_id=77, trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP) is False
