"""Regression tests: VAT module does not break any existing endpoints."""

from datetime import date

from app.clients.models.client import Client, ClientType


def test_vat_module_does_not_break_binder_receive(client, advisor_headers, test_db):
    """Regression: binder receive still works after VAT module loaded."""
    c = Client(
        full_name="Regression VAT Client",
        id_number="VAT_REG_001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": c.id,
            "binder_number": "VAT-REG-001",
            "binder_type": "vat",
            "received_at": "2026-02-01",
            "received_by": 1,
        },
    )
    assert response.status_code == 201


def test_vat_module_does_not_break_charges(client, advisor_headers, test_db):
    """Regression: charges still work after VAT module loaded."""
    c = Client(
        full_name="Regression VAT Billing",
        id_number="VAT_REG_002",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"client_id": c.id, "amount": 500.0, "charge_type": "one_time"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_vat_module_does_not_break_health(client):
    """Regression: health endpoint unaffected."""
    response = client.get("/health")
    assert response.status_code == 200
