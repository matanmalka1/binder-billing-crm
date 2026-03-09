from datetime import date

from app.clients.models import Client, ClientType


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Client A",
        id_number="111111111",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_advisor_can_create_charge(client, advisor_headers, test_db):
    c = _create_client(test_db)
    res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "client_id": c.id,
            "amount": 100.0,
            "charge_type": "one_time",
            "period": "2026-02",
            "currency": "ILS",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["client_id"] == c.id
    assert data["amount"] == 100.0
    assert data["charge_type"] == "one_time"
    assert data["period"] == "2026-02"
    assert data["currency"] == "ILS"
    assert data["status"] == "draft"
    assert data["issued_at"] is None
    assert data["paid_at"] is None


def test_secretary_cannot_mutate_charges(client, secretary_headers, advisor_headers, test_db):
    c = _create_client(test_db)
    create_res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"client_id": c.id, "amount": 50.0, "charge_type": "retainer"},
    )
    charge_id = create_res.json()["id"]

    assert (
        client.post("/api/v1/charges", headers=secretary_headers, json={"client_id": c.id, "amount": 1, "charge_type": "one_time"}).status_code
        == 403
    )
    assert client.post(f"/api/v1/charges/{charge_id}/issue", headers=secretary_headers).status_code == 403
    assert client.post(f"/api/v1/charges/{charge_id}/mark-paid", headers=secretary_headers).status_code == 403
    assert client.post(f"/api/v1/charges/{charge_id}/cancel", headers=secretary_headers).status_code == 403


def test_secretary_can_read_charges(client, secretary_headers, advisor_headers, test_db):
    c = _create_client(test_db)
    create_res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"client_id": c.id, "amount": 75.0, "charge_type": "one_time"},
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
