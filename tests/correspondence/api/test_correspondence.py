from datetime import date, datetime

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.services.correspondence_service import CorrespondenceService


def _create_business(test_db, id_number: str = "777777777") -> Business:
    client = Client(
        full_name="Correspondence Client",
        id_number=id_number,
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"Business {id_number}",
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def _create_contact(test_db, business: Business) -> AuthorityContact:
    contact = AuthorityContact(
        business_id=business.id,
        contact_type=ContactType.ASSESSING_OFFICER,
        name="Assessing Officer",
        phone="0501234567",
    )
    test_db.add(contact)
    test_db.commit()
    test_db.refresh(contact)
    return contact


def test_create_correspondence_with_contact(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business)

    response = client.post(
        f"/api/v1/businesses/{business.id}/correspondence",
        headers=advisor_headers,
        json={
            "contact_id": contact.id,
            "correspondence_type": "call",
            "subject": "Status check",
            "notes": "Asked about refund ETA",
            "occurred_at": "2026-02-10T10:00:00",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["business_id"] == business.id
    assert data["contact_id"] == contact.id
    assert data["correspondence_type"] == "call"
    assert data["subject"] == "Status check"
    assert data["created_by"] == test_user.id


def test_create_correspondence_invalid_type_returns_422(client, test_db, advisor_headers):
    business = _create_business(test_db)

    response = client.post(
        f"/api/v1/businesses/{business.id}/correspondence",
        headers=advisor_headers,
        json={
            "correspondence_type": "invalid_type",
            "subject": "Invalid type attempt",
            "occurred_at": "2026-02-10T10:00:00",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_create_correspondence_contact_mismatch_returns_403(client, test_db, advisor_headers):
    owner_business = _create_business(test_db, id_number="777777777")
    other_business = _create_business(test_db, id_number="888888888")
    contact = _create_contact(test_db, owner_business)

    response = client.post(
        f"/api/v1/businesses/{other_business.id}/correspondence",
        headers=advisor_headers,
        json={
            "contact_id": contact.id,
            "correspondence_type": "email",
            "subject": "Wrong business contact",
            "occurred_at": "2026-02-11T09:00:00",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == "CORRESPONDENCE.FORBIDDEN_CONTACT"


def test_list_correspondence_ordered_desc_and_get_by_id(client, test_db, advisor_headers, test_user):
    business = _create_business(test_db)
    service = CorrespondenceService(test_db)

    earlier = service.add_entry(
        business_id=business.id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="Earlier entry",
        occurred_at=datetime(2026, 2, 1, 9, 0, 0),
        created_by=test_user.id,
    )
    later = service.add_entry(
        business_id=business.id,
        correspondence_type=CorrespondenceType.MEETING,
        subject="Later entry",
        occurred_at=datetime(2026, 2, 5, 9, 0, 0),
        created_by=test_user.id,
    )

    list_response = client.get(
        f"/api/v1/businesses/{business.id}/correspondence",
        headers=advisor_headers,
    )

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 2
    assert items[0]["id"] == later.id
    assert items[1]["id"] == earlier.id

    get_response = client.get(
        f"/api/v1/businesses/{business.id}/correspondence/{later.id}",
        headers=advisor_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == later.id
