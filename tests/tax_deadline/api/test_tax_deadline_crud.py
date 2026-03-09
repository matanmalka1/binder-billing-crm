from datetime import date, timedelta
from decimal import Decimal

from app.clients.models import Client, ClientType


def _make_client(db):
    client = Client(
        full_name="Deadline CRUD Client",
        id_number="DL-CRUD-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_tax_deadline_full_crud_flow(client, test_db, advisor_headers):
    crm_client = _make_client(test_db)
    due_date = date.today() + timedelta(days=3)

    # Create
    create_resp = client.post(
        "/api/v1/tax-deadlines",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
            "deadline_type": "vat",
            "due_date": due_date.isoformat(),
            "payment_amount": 150.0,
            "description": "VAT payment",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    deadline_id = created["id"]
    assert created["status"] == "pending"
    assert created["payment_amount"] == 150.0

    # List (global) includes the new deadline
    list_resp = client.get("/api/v1/tax-deadlines", headers=advisor_headers)
    assert list_resp.status_code == 200
    listed_ids = {item["id"] for item in list_resp.json()["items"]}
    assert deadline_id in listed_ids

    # Get by id
    get_resp = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["client_id"] == crm_client.id

    # Update payment amount and description
    update_resp = client.put(
        f"/api/v1/tax-deadlines/{deadline_id}",
        headers=advisor_headers,
        json={"payment_amount": 175.5, "description": "Updated VAT"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["payment_amount"] == 175.5
    assert updated["description"] == "Updated VAT"

    # Complete
    complete_resp = client.post(
        f"/api/v1/tax-deadlines/{deadline_id}/complete",
        headers=advisor_headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    # Delete
    delete_resp = client.delete(
        f"/api/v1/tax-deadlines/{deadline_id}",
        headers=advisor_headers,
    )
    assert delete_resp.status_code == 204

    # Fetch after delete should 404
    not_found = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert not_found.status_code == 404
