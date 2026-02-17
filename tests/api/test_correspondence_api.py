from datetime import date, datetime

from app.models import Client, ClientType
from app.models.authority_contact import AuthorityContact, ContactType
from app.models.correspondence import CorrespondenceType
from app.services.correspondence_service import CorrespondenceService


def _create_client(test_db, id_number: str = "777777777") -> Client:
    client = Client(
        full_name="Correspondence Client",
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def _create_contact(test_db, client: Client) -> AuthorityContact:
    contact = AuthorityContact(
        client_id=client.id,
        contact_type=ContactType.ASSESSING_OFFICER,
        name="Assessing Officer",
        phone="0501234567",
    )
    test_db.add(contact)
    test_db.commit()
    test_db.refresh(contact)
    return contact


def test_create_correspondence_with_contact(client, test_db, advisor_headers, test_user):
    corr_client = _create_client(test_db)
    contact = _create_contact(test_db, corr_client)

    response = client.post(
        f"/api/v1/clients/{corr_client.id}/correspondence",
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
    assert data["client_id"] == corr_client.id
    assert data["contact_id"] == contact.id
    assert data["correspondence_type"] == "call"
    assert data["subject"] == "Status check"
    assert data["created_by"] == test_user.id


def test_create_correspondence_invalid_type_returns_400(client, test_db, advisor_headers):
    corr_client = _create_client(test_db)

    response = client.post(
        f"/api/v1/clients/{corr_client.id}/correspondence",
        headers=advisor_headers,
        json={
            "correspondence_type": "fax",
            "subject": "Invalid type attempt",
            "occurred_at": "2026-02-10T10:00:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid correspondence_type: fax"


def test_create_correspondence_contact_mismatch_returns_400(client, test_db, advisor_headers):
    owner_client = _create_client(test_db, id_number="777777777")
    other_client = _create_client(test_db, id_number="888888888")
    contact = _create_contact(test_db, owner_client)

    response = client.post(
        f"/api/v1/clients/{other_client.id}/correspondence",
        headers=advisor_headers,
        json={
            "contact_id": contact.id,
            "correspondence_type": "email",
            "subject": "Wrong client contact",
            "occurred_at": "2026-02-11T09:00:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Contact {contact.id} does not belong to client {other_client.id}"
    )


def test_list_correspondence_ordered_desc(client, test_db, advisor_headers, test_user):
    corr_client = _create_client(test_db)
    service = CorrespondenceService(test_db)

    earlier = service.add_entry(
        client_id=corr_client.id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="Earlier entry",
        occurred_at=datetime(2026, 2, 1, 9, 0, 0),
        created_by=test_user.id,
    )
    later = service.add_entry(
        client_id=corr_client.id,
        correspondence_type=CorrespondenceType.MEETING,
        subject="Later entry",
        occurred_at=datetime(2026, 2, 5, 9, 0, 0),
        created_by=test_user.id,
    )

    response = client.get(
        f"/api/v1/clients/{corr_client.id}/correspondence",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # Should be ordered by occurred_at DESC
    assert items[0]["id"] == later.id
    assert items[1]["id"] == earlier.id
