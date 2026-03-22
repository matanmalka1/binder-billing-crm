from datetime import date

from app.authority_contact.models.authority_contact import ContactType
from app.authority_contact.repositories.authority_contact_repository import AuthorityContactRepository
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client


def _create_business(test_db) -> Business:
    client = Client(
        full_name="Authority Contact Client",
        id_number="777777777",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Authority Contact Business",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def _create_contact(test_db, business_id: int, contact_type: ContactType = ContactType.VAT_BRANCH):
    return AuthorityContactRepository(test_db).create(
        business_id=business_id,
        contact_type=contact_type,
        name="Branch Contact",
        office="Tel Aviv",
        phone="03-1234567",
        email="branch@example.com",
    )


def test_create_authority_contact(client, test_db, advisor_headers):
    business = _create_business(test_db)

    response = client.post(
        f"/api/v1/businesses/{business.id}/authority-contacts",
        headers=advisor_headers,
        json={
            "contact_type": "vat_branch",
            "name": "Ms. VAT",
            "office": "Central",
            "phone": "03-0000000",
            "email": "vat@example.com",
            "notes": "Handles VAT filings",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["business_id"] == business.id
    assert data["contact_type"] == "vat_branch"
    assert data["name"] == "Ms. VAT"
    assert data["created_at"] is not None

    # Persisted
    stored = AuthorityContactRepository(test_db).get_by_id(data["id"])
    assert stored is not None
    assert stored.contact_type == ContactType.VAT_BRANCH


def test_create_authority_contact_unknown_business_returns_404(client, advisor_headers):
    response = client.post(
        "/api/v1/businesses/999/authority-contacts",
        headers=advisor_headers,
        json={"contact_type": "vat_branch", "name": "Ghost"},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "BUSINESS.NOT_FOUND"


def test_create_authority_contact_invalid_contact_type_returns_422(client, test_db, advisor_headers):
    business = _create_business(test_db)

    response = client.post(
        f"/api/v1/businesses/{business.id}/authority-contacts",
        headers=advisor_headers,
        json={
            "contact_type": "invalid_type",
            "name": "Bad Type",
        },
    )

    assert response.status_code == 422


def test_list_authority_contacts_filters_by_type(client, test_db, advisor_headers):
    business = _create_business(test_db)
    _create_contact(test_db, business.id, ContactType.VAT_BRANCH)
    _create_contact(test_db, business.id, ContactType.ASSESSING_OFFICER)
    _create_contact(test_db, business.id, ContactType.VAT_BRANCH)

    response = client.get(
        f"/api/v1/businesses/{business.id}/authority-contacts?contact_type=vat_branch&page=1&page_size=10",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert all(item["contact_type"] == "vat_branch" for item in data["items"])


def test_list_authority_contacts_invalid_contact_type_returns_422(client, test_db, advisor_headers):
    business = _create_business(test_db)

    response = client.get(
        f"/api/v1/businesses/{business.id}/authority-contacts?contact_type=invalid_type",
        headers=advisor_headers,
    )

    assert response.status_code == 422


def test_update_authority_contact(client, test_db, advisor_headers):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business.id, ContactType.VAT_BRANCH)

    response = client.patch(
        f"/api/v1/businesses/authority-contacts/{contact.id}",
        headers=advisor_headers,
        json={"name": "Updated Name", "contact_type": "assessing_officer"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["contact_type"] == "assessing_officer"
    assert data["updated_at"] is not None


def test_update_authority_contact_invalid_contact_type_returns_422(client, test_db, advisor_headers):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business.id, ContactType.VAT_BRANCH)

    response = client.patch(
        f"/api/v1/businesses/authority-contacts/{contact.id}",
        headers=advisor_headers,
        json={"contact_type": "invalid_type"},
    )

    assert response.status_code == 422


def test_delete_authority_contact_soft_deletes(client, test_db, advisor_headers):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business.id)

    response = client.delete(
        f"/api/v1/businesses/authority-contacts/{contact.id}",
        headers=advisor_headers,
    )

    assert response.status_code == 204

    # Soft-deleted contact should be hidden
    repo = AuthorityContactRepository(test_db)
    assert repo.get_by_id(contact.id) is None
    list_response = client.get(
        f"/api/v1/businesses/{business.id}/authority-contacts",
        headers=advisor_headers,
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0


def test_secretary_cannot_delete_authority_contact(client, test_db, secretary_headers):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business.id)

    response = client.delete(
        f"/api/v1/businesses/authority-contacts/{contact.id}",
        headers=secretary_headers,
    )

    assert response.status_code == 403


def test_get_authority_contact_by_id_and_not_found(client, test_db, advisor_headers):
    business = _create_business(test_db)
    contact = _create_contact(test_db, business.id)

    ok = client.get(f"/api/v1/businesses/authority-contacts/{contact.id}", headers=advisor_headers)
    assert ok.status_code == 200
    assert ok.json()["id"] == contact.id

    missing = client.get("/api/v1/businesses/authority-contacts/999999", headers=advisor_headers)
    assert missing.status_code == 404
