from datetime import date

from app.clients.models.client import Client, ClientType


def test_binder_receive_accepts_and_stores_binder(client, advisor_headers, test_db):
    """Test binder receive unchanged."""
    test_client = Client(
        full_name="S5 Regression Client",
        id_number="555555550",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": test_client.id,
            "binder_number": "S5-REG-001",
            "binder_type": "other",
            "received_at": "2026-02-09",
            "received_by": 1,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder_number"] == "S5-REG-001"
    assert data["status"] == "in_office"


def test_open_binders_endpoint_includes_items(client, advisor_headers):
    """Test operational endpoints unchanged."""
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_charges_endpoint_creates_draft_charge(client, advisor_headers, test_db):
    """Test billing unchanged."""
    test_client = Client(
        full_name="S5 Billing Client",
        id_number="555555551",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "client_id": test_client.id,
            "amount": 100.0,
            "charge_type": "one_time",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"


def test_document_signals_endpoint_returns_missing_documents(client, advisor_headers, secretary_headers, test_db):
    """Test notifications unchanged."""
    test_client = Client(
        full_name="S5 Notification Client",
        id_number="555555552",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.get(
        f"/api/v1/documents/client/{test_client.id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "missing_documents" in data
