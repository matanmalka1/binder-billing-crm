from datetime import date

from app.businesses.models.business import Business, EntityType
from app.clients.models.client import Client


def _create_business(test_db) -> Business:
    client = Client(full_name="Client A", id_number="111111111")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        entity_type=EntityType.COMPANY_LTD,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_advisor_can_create_charge(client, advisor_headers, test_db):
    business = _create_business(test_db)
    res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "amount": 100.0,
            "charge_type": "consultation_fee",
            "period": "2026-02",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["business_id"] == business.id
    assert data["amount"] == "100.00"
    assert data["charge_type"] == "consultation_fee"
    assert data["period"] == "2026-02"
    assert data["status"] == "draft"
    assert data["issued_at"] is None
    assert data["paid_at"] is None


def test_secretary_cannot_mutate_charges(client, secretary_headers, advisor_headers, test_db):
    business = _create_business(test_db)
    create_res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"business_id": business.id, "amount": 50.0, "charge_type": "monthly_retainer"},
    )
    charge_id = create_res.json()["id"]

    assert (
        client.post(
            "/api/v1/charges",
            headers=secretary_headers,
            json={"business_id": business.id, "amount": 1, "charge_type": "other"},
        ).status_code
        == 403
    )
    assert client.post(f"/api/v1/charges/{charge_id}/issue", headers=secretary_headers).status_code == 403
    assert client.post(f"/api/v1/charges/{charge_id}/mark-paid", headers=secretary_headers).status_code == 403
    assert client.post(f"/api/v1/charges/{charge_id}/cancel", headers=secretary_headers).status_code == 403


def test_secretary_can_read_charges(client, secretary_headers, advisor_headers, test_db):
    business = _create_business(test_db)
    create_res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"business_id": business.id, "amount": 75.0, "charge_type": "consultation_fee"},
    )
    charge_id = create_res.json()["id"]

    list_res = client.get("/api/v1/charges", headers=secretary_headers)
    assert list_res.status_code == 200
    payload = list_res.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == charge_id

    get_res = client.get(f"/api/v1/charges/{charge_id}", headers=secretary_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == charge_id


def test_charges_requires_auth(client):
    assert client.get("/api/v1/charges").status_code == 401
    assert client.get("/api/v1/charges", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
