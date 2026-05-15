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


def _seed_notification(test_db, business_id: int, content: str):
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
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
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


def test_notifications_unread_count(client, test_db, advisor_headers):
    b1 = _business(test_db, "3")
    _seed_notification(test_db, b1.id, "a")
    _seed_notification(test_db, b1.id, "b")

    resp = client.get(
        f"/api/v1/notifications/unread-count?business_id={b1.id}",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 2
