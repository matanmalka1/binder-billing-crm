from datetime import date

from app.businesses.models.business import Business
from app.common.enums import IdNumberType
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.client_record import ClientRecord
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.notification.models.notification import (
    NotificationChannel,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository


def _business(test_db, suffix: str) -> Business:
    le = LegalEntity(
        id_number=f"7300000{suffix}",
        id_number_type=IdNumberType.INDIVIDUAL,
        official_name=f"Notification API Client {suffix}",
    )
    test_db.add(le)
    test_db.flush()

    cr = ClientRecord(legal_entity_id=le.id)
    test_db.add(cr)
    test_db.flush()

    person = Person(
        full_name=f"Notification API Client {suffix}",
        id_number=f"7300000{suffix}",
        id_number_type=IdNumberType.INDIVIDUAL,
        email=f"n{suffix}@example.com",
        phone=f"0500000{suffix}",
    )
    test_db.add(person)
    test_db.flush()

    link = PersonLegalEntityLink(
        person_id=person.id,
        legal_entity_id=le.id,
        role=PersonLegalEntityRole.OWNER,
    )
    test_db.add(link)
    test_db.flush()

    b = Business(
        legal_entity_id=le.id,
        business_name=f"Notification API Biz {suffix}",
        opened_at=date.today(),
    )
    test_db.add(b)
    test_db.commit()
    test_db.refresh(b)
    return b


def _seed_notification(test_db, business_id: int, content: str, **kwargs):
    business = test_db.get(Business, business_id)
    cr = (
        test_db.query(ClientRecord)
        .filter(ClientRecord.legal_entity_id == business.legal_entity_id)
        .first()
    )
    repo = NotificationRepository(test_db)
    return repo.create(
        client_record_id=cr.id,
        business_id=business_id,
        trigger=kwargs.get("trigger", NotificationTrigger.MANUAL_PAYMENT_REMINDER),
        channel=kwargs.get("channel", NotificationChannel.EMAIL),
        recipient="x@example.com",
        content_snapshot=content,
    )


def test_notifications_list(client, test_db, advisor_headers):
    b1 = _business(test_db, "1")
    b2 = _business(test_db, "2")

    n1 = _seed_notification(test_db, b1.id, "one")
    n2 = _seed_notification(test_db, b1.id, "two")
    _seed_notification(test_db, b2.id, "other")

    resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}&page=1&page_size=10",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert {item["id"] for item in data["items"]} == {n1.id, n2.id}


def test_notifications_list_by_status(client, test_db, advisor_headers):
    b1 = _business(test_db, "s1")
    n_pending = _seed_notification(test_db, b1.id, "pending-one")
    n_sent = _seed_notification(test_db, b1.id, "sent-one")
    repo = NotificationRepository(test_db)
    repo.mark_sent(n_sent.id)
    test_db.commit()

    resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}&status=pending",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == n_pending.id


def test_notifications_list_by_trigger(client, test_db, advisor_headers):
    b1 = _business(test_db, "t1")
    n_manual = _seed_notification(
        test_db, b1.id, "manual", trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER
    )
    _seed_notification(
        test_db, b1.id, "binder", trigger=NotificationTrigger.BINDER_RECEIVED
    )

    resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}&trigger=manual_payment_reminder",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == n_manual.id


def test_notifications_list_by_channel(client, test_db, advisor_headers):
    b1 = _business(test_db, "c1")
    n_email = _seed_notification(
        test_db, b1.id, "email-notif", channel=NotificationChannel.EMAIL
    )
    _seed_notification(test_db, b1.id, "wa-notif", channel=NotificationChannel.WHATSAPP)

    resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}&channel=email",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == n_email.id


def test_notifications_summary(client, test_db, advisor_headers):
    b1 = _business(test_db, "sum1")
    repo = NotificationRepository(test_db)

    n_sent = _seed_notification(test_db, b1.id, "sent")
    repo.mark_sent(n_sent.id)
    n_failed = _seed_notification(test_db, b1.id, "failed")
    repo.mark_failed(n_failed.id, "err")
    _seed_notification(test_db, b1.id, "still-pending")
    test_db.commit()

    resp = client.get(
        f"/api/v1/notifications/summary?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 1
    assert data["failed"] == 1
    assert data["pending"] == 1
    assert data["total"] == 3


def test_notifications_summary_zero_for_absent_statuses(
    client, test_db, advisor_headers
):
    b1 = _business(test_db, "sum2")
    repo = NotificationRepository(test_db)
    n = _seed_notification(test_db, b1.id, "sent-only")
    repo.mark_sent(n.id)
    test_db.commit()

    resp = client.get(
        f"/api/v1/notifications/summary?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == 0
    assert data["failed"] == 0
    assert data["sent"] == 1
    assert data["total"] == 1


def test_unread_count_route_gone(client, advisor_headers):
    resp = client.get("/api/v1/notifications/unread-count", headers=advisor_headers)
    assert resp.status_code == 404


def test_secretary_can_list(client, test_db, secretary_headers):
    b1 = _business(test_db, "sec1")
    _seed_notification(test_db, b1.id, "sec-notif")

    resp = client.get(
        f"/api/v1/notifications?business_id={b1.id}",
        headers=secretary_headers,
    )
    assert resp.status_code == 200


def test_secretary_cannot_send(client, test_db, secretary_headers):
    b1 = _business(test_db, "sec2")
    cr = (
        test_db.query(ClientRecord)
        .filter(ClientRecord.legal_entity_id == b1.legal_entity_id)
        .first()
    )
    resp = client.post(
        "/api/v1/notifications/send",
        json={
            "client_record_id": cr.id,
            "message": "test",
        },
        headers=secretary_headers,
    )
    assert resp.status_code == 403
