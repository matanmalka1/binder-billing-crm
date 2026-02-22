from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.clients.models.client import Client, ClientType


def test_sprint1_binder_receive_still_works(client, advisor_headers, test_db):
    """Regression: Sprint 1 binder receive endpoint unchanged."""
    test_client = Client(
        full_name="Regression Test Client",
        id_number="000000003",
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
            "binder_number": "REG-001",
            "binder_type": "other",
            "received_at": "2026-02-09",
            "received_by": 1,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["binder_number"] == "REG-001"
    assert data["status"] == "in_office"


def test_sprint2_operational_endpoints_unchanged(client, advisor_headers, test_db, test_user):
    """Regression: Sprint 2 operational endpoints unchanged."""
    test_client = Client(
        full_name="Sprint2 Regression Client",
        id_number="000000004",
        client_type=ClientType.OSEK_PATUR,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    binder = Binder(
        client_id=test_client.id,
        binder_number="REG-002",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=100),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    # Test open binders endpoint
    response = client.get("/api/v1/binders/open", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()


def test_sprint3_billing_endpoints_unchanged(client, advisor_headers, test_db):
    """Regression: Sprint 3 billing endpoints unchanged."""
    test_client = Client(
        full_name="Sprint3 Regression Client",
        id_number="000000005",
        client_type=ClientType.EMPLOYEE,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    # Test charge creation
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
    assert data["amount"] == 100.0
    assert data["status"] == "draft"

    # Test charge list
    response = client.get("/api/v1/charges", headers=advisor_headers)
    assert response.status_code == 200
    assert "items" in response.json()
