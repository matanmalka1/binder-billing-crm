from datetime import date

from app.clients.models import Client, ClientType


def _client(db) -> Client:
    crm_client = Client(
        full_name="Deadline Generate API Client",
        id_number="TDGAPI001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_generate_deadlines_endpoint_success(client, test_db, advisor_headers):
    crm_client = _client(test_db)

    resp = client.post(
        "/api/v1/tax-deadlines/generate",
        headers=advisor_headers,
        json={"client_id": crm_client.id, "year": 2026},
    )

    assert resp.status_code == 201
    assert resp.json()["created_count"] >= 13


def test_generate_deadlines_endpoint_advisor_only(client, test_db, secretary_headers):
    crm_client = _client(test_db)

    resp = client.post(
        "/api/v1/tax-deadlines/generate",
        headers=secretary_headers,
        json={"client_id": crm_client.id, "year": 2026},
    )

    assert resp.status_code == 403
