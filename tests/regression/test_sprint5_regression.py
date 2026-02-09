"""Regression tests for Sprint 5 hardening."""
from datetime import date, timedelta

from app.models import Binder, BinderStatus, Client, ClientType


def test_sprint1_unchanged(client, advisor_headers, test_db):
    """Test Sprint 1 binder receive unchanged."""
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
            "received_at": "2026-02-09",
            "received_by": 1,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder_number"] == "S5-REG-001"
    assert data["status"] == "in_office"


def test_sprint2_unchanged(client, advisor_headers):
    """Test Sprint 2 operational endpoints unchanged."""
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()

    response = client.get("/api/v1/binders/overdue", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_sprint3_unchanged(client, advisor_headers, test_db):
    """Test Sprint 3 billing unchanged."""
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


def test_sprint4_unchanged(client, advisor_headers, secretary_headers, test_db):
    """Test Sprint 4 notifications unchanged."""
    test_client = Client(
        full_name="S5 Notification Client",
        id_number="555555552",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    # Test operational signals (Sprint 4)
    response = client.get(
        f"/api/v1/documents/client/{test_client.id}/signals",
        headers=secretary_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "missing_documents" in data
    assert "binders_nearing_sla" in data