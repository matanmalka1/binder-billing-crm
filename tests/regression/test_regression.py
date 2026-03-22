from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client


def test_binder_receive_endpoint_creates_in_office_binder(client, advisor_headers, test_db):
    """Regression: binder receive endpoint unchanged."""
    test_client = Client(
        full_name="Regression Test Client",
        id_number="000000003",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": test_client.id,
            "binder_number": "REG-001",
            "period_start": "2026-01-01",
            "binder_type": "other",
            "received_at": "2026-02-09",
            "received_by": 1,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder"]["binder_number"] == "REG-001"
    assert data["binder"]["status"] == "in_office"


def test_open_binders_endpoint_returns_items(client, advisor_headers, test_db, test_user):
    """Regression: operational endpoints unchanged."""
    test_client = Client(
        full_name="Regression Client",
        id_number="000000004",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    binder = Binder(
        client_id=test_client.id,
        binder_number="REG-002",
        period_start=date.today() - timedelta(days=100),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    # Test open binders endpoint
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_charges_endpoints_create_and_list_draft_charge(client, advisor_headers, test_db):
    """Regression: billing endpoints unchanged."""
    test_client = Client(
        full_name="Regression Client",
        id_number="000000005",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    # Test charge creation
    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": test_client.id,
            "amount": 100.0,
            "charge_type": "other",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert float(data["amount"]) == 100.0
    assert data["status"] == "draft"

    # Test charge list
    response = client.get("/api/v1/charges", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()
