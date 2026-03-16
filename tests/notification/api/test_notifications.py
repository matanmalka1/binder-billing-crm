from datetime import date

from app.clients.models.client import Client, ClientType
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def _client(test_db, suffix: str) -> Client:
    c = Client(
        full_name=f"Notification API Client {suffix}",
        id_number=f"NTF-API-{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
        email=f"n{suffix}@example.com",
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def _seed_notification(test_db, client_id: int, content: str):
    repo = NotificationRepository(test_db)
    return repo.create(
        client_id=client_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="x@example.com",
        content_snapshot=content,
    )


def test_notifications_read_lifecycle(client, test_db, advisor_headers):
    c1 = _client(test_db, "1")
    c2 = _client(test_db, "2")

    n1 = _seed_notification(test_db, c1.id, "one")
    n2 = _seed_notification(test_db, c1.id, "two")
    _seed_notification(test_db, c2.id, "other")

    list_resp = client.get(f"/api/v1/notifications?client_id={c1.id}&limit=10", headers=advisor_headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 2
    assert {item["id"] for item in listed} == {n1.id, n2.id}

    unread_before = client.get(f"/api/v1/notifications/unread-count?client_id={c1.id}", headers=advisor_headers)
    assert unread_before.status_code == 200
    assert unread_before.json()["unread_count"] == 2

    mark_one = client.post(
        "/api/v1/notifications/mark-read",
        headers=advisor_headers,
        json={"notification_ids": [n1.id]},
    )
    assert mark_one.status_code == 200
    assert mark_one.json()["updated"] == 1

    unread_after_one = client.get(f"/api/v1/notifications/unread-count?client_id={c1.id}", headers=advisor_headers)
    assert unread_after_one.status_code == 200
    assert unread_after_one.json()["unread_count"] == 1

    mark_all = client.post(f"/api/v1/notifications/mark-all-read?client_id={c1.id}", headers=advisor_headers)
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] == 1

    unread_after_all = client.get(f"/api/v1/notifications/unread-count?client_id={c1.id}", headers=advisor_headers)
    assert unread_after_all.status_code == 200
    assert unread_after_all.json()["unread_count"] == 0
