from datetime import date

from app.clients.models import Client, ClientType


def _client(db) -> Client:
    crm_client = Client(
        full_name="Advance Gen API Client",
        id_number="APGAPI001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_generate_schedule_endpoint_returns_counts(client, test_db, advisor_headers):
    crm_client = _client(test_db)

    resp = client.post(
        "/api/v1/advance-payments/generate",
        headers=advisor_headers,
        json={"client_id": crm_client.id, "year": 2026},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] == 12
    assert payload["skipped"] == 0


def test_generate_schedule_endpoint_is_advisor_only(client, test_db, secretary_headers):
    crm_client = _client(test_db)

    resp = client.post(
        "/api/v1/advance-payments/generate",
        headers=secretary_headers,
        json={"client_id": crm_client.id, "year": 2026},
    )

    assert resp.status_code == 403
