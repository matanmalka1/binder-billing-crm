from datetime import date

from app.businesses.models.business import Business, EntityType
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository


def _business(test_db, suffix: str) -> Business:
    c = Client(
        full_name=f"Notification API Client {suffix}",
        id_number=f"7300000{suffix}",
        email=f"n{suffix}@example.com",
        phone=f"0500000{suffix}",
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)

    b = Business(
        client_id=c.id,
        business_name=f"Notification API Biz {suffix}",
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date.today(),
    )
    test_db.add(b)
    test_db.commit()
    test_db.refresh(b)
    return b


def _seed_notification(test_db, business_id: int, content: str):
    repo = NotificationRepository(test_db)
    return repo.create(
        business_id=business_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="x@example.com",
        content_snapshot=content,
    )


def test_notifications_read_lifecycle(client, test_db, advisor_headers):
    b1 = _business(test_db, "1")
    b2 = _business(test_db, "2")

    n1 = _seed_notification(test_db, b1.id, "one")
    n2 = _seed_notification(test_db, b1.id, "two")
    _seed_notification(test_db, b2.id, "other")

    list_resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["total"] == 2
    assert len(listed["items"]) == 2
    assert {item["id"] for item in listed["items"]} == {n1.id, n2.id}

    unread_before = client.get(
        f"/api/v1/notifications/unread-count?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert unread_before.status_code == 200
    assert unread_before.json()["unread_count"] == 2

    mark_one = client.post(
        "/api/v1/notifications/mark-read",
        headers=advisor_headers,
        json={"notification_ids": [n1.id]},
    )
    assert mark_one.status_code == 200
    assert mark_one.json()["updated"] == 1

    unread_after_one = client.get(
        f"/api/v1/notifications/unread-count?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert unread_after_one.status_code == 200
    assert unread_after_one.json()["unread_count"] == 1

    mark_all = client.post(f"/api/v1/notifications/mark-all-read?business_id={b1.id}", headers=advisor_headers)
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] == 1

    unread_after_all = client.get(
        f"/api/v1/notifications/unread-count?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert unread_after_all.status_code == 200
    assert unread_after_all.json()["unread_count"] == 0


def test_notifications_send_endpoint_advisor_only(client, test_db, advisor_headers, secretary_headers):
    business = _business(test_db, "3")

    advisor_send = client.post(
        "/api/v1/notifications/send",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "channel": "email",
            "message": "manual reminder",
            "severity": "urgent",
        },
    )
    assert advisor_send.status_code == 200
    assert advisor_send.json() == {"ok": True}

    repo = NotificationRepository(test_db)
    rows = repo.list_by_business(business.id)
    assert len(rows) == 1
    assert rows[0].trigger == NotificationTrigger.MANUAL_PAYMENT_REMINDER
    assert rows[0].severity == NotificationSeverity.URGENT

    secretary_send = client.post(
        "/api/v1/notifications/send",
        headers=secretary_headers,
        json={"business_id": business.id, "channel": "email", "message": "x"},
    )
    assert secretary_send.status_code == 403


def test_notifications_mark_read_validation_error(client, advisor_headers):
    resp = client.post(
        "/api/v1/notifications/mark-read",
        headers=advisor_headers,
        json={"notification_ids": []},
    )
    assert resp.status_code == 422
