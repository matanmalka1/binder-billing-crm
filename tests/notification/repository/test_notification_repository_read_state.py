from datetime import date

from app.clients.models.client import Client, ClientType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def _client(test_db, suffix: str) -> Client:
    c = Client(
        full_name=f"Notif Repo Client {suffix}",
        id_number=f"NTF-REP-{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
        email=f"repo{suffix}@example.com",
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def _create(repo: NotificationRepository, client_id: int, msg: str):
    return repo.create(
        client_id=client_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="x@example.com",
        content_snapshot=msg,
    )


def test_notification_repository_read_and_recent_methods(test_db):
    repo = NotificationRepository(test_db)
    c1 = _client(test_db, "1")
    c2 = _client(test_db, "2")

    n1 = _create(repo, c1.id, "a")
    n2 = _create(repo, c1.id, "b")
    n3 = _create(repo, c2.id, "c")

    assert repo.get_by_id(n1.id) is not None
    assert repo.count_unread(client_id=c1.id) == 2

    updated = repo.mark_read([n1.id])
    assert updated == 1
    assert repo.count_unread(client_id=c1.id) == 1

    updated_all = repo.mark_all_read(client_id=c1.id)
    assert updated_all == 1
    assert repo.count_unread(client_id=c1.id) == 0
    assert repo.count_unread() == 1

    recent_c2 = repo.list_recent(limit=10, client_id=c2.id)
    assert [n.id for n in recent_c2] == [n3.id]
