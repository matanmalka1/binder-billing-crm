from datetime import date

from app.clients.models import Client, ClientType


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Tax Profile Client",
        id_number="555555555",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_get_returns_null_profile_when_absent(client, test_db, advisor_headers):
    tax_client = _create_client(test_db)

    response = client.get(
        f"/api/v1/clients/{tax_client.id}/tax-profile",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == tax_client.id
    assert data["vat_type"] is None
    assert data["business_type"] is None
    assert data["tax_year_start"] is None
    assert data["accountant_name"] is None


def test_update_tax_profile_success(client, test_db, advisor_headers):
    tax_client = _create_client(test_db)

    response = client.patch(
        f"/api/v1/clients/{tax_client.id}/tax-profile",
        headers=advisor_headers,
        json={
            "vat_type": "monthly",
            "business_type": "llc",
            "tax_year_start": 4,
            "accountant_name": "Jane CPA",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == tax_client.id
    assert data["vat_type"] == "monthly"
    assert data["business_type"] == "llc"
    assert data["tax_year_start"] == 4
    assert data["accountant_name"] == "Jane CPA"
    # created_at is set on first write; updated_at stays None on insert
    assert data["created_at"] is not None
    assert data["updated_at"] is None

    # Round-trip check
    follow_up = client.get(
        f"/api/v1/clients/{tax_client.id}/tax-profile",
        headers=advisor_headers,
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["vat_type"] == "monthly"


def test_update_tax_profile_invalid_vat_type_returns_400(client, test_db, advisor_headers):
    tax_client = _create_client(test_db)

    response = client.patch(
        f"/api/v1/clients/{tax_client.id}/tax-profile",
        headers=advisor_headers,
        json={"vat_type": "weekly"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid vat_type: weekly"


def test_tax_profile_unknown_client_returns_404(client, advisor_headers):
    response = client.get(
        "/api/v1/clients/999/tax-profile",
        headers=advisor_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"
