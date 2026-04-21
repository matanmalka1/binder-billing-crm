"""Regression tests: VAT module does not break any existing endpoints."""

from tests.helpers.identity import seed_client_identity, seed_client_with_business


def test_vat_module_keeps_binder_receive_working(client, advisor_headers, test_db):
    """Regression: binder receive still works after VAT module loaded."""
    c = seed_client_identity(
        test_db,
        full_name="Regression VAT Client",
        id_number="VAT_REG_001",
        office_client_number=701,
    )
    test_db.commit()

    response = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_record_id": c.id,
            "received_at": "2026-02-01",
            "received_by": 1,
            "materials": [
                {
                    "material_type": "vat",
                    "period_year": 2026,
                    "period_month_start": 1,
                    "period_month_end": 1,
                }
            ],
        },
    )
    assert response.status_code == 201


def test_vat_module_keeps_charge_creation_working(client, advisor_headers, test_db):
    """Regression: charge creation still works after VAT module loaded."""
    c, business = seed_client_with_business(
        test_db,
        full_name="Regression VAT Billing",
        id_number="VAT_REG_002",
    )
    test_db.commit()

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "client_record_id": c.id,
            "business_id": business.id if business else None,
            "amount": 500.0,
            "charge_type": "other",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_vat_module_keeps_health_endpoint_working(client):
    """Regression: health endpoint unaffected."""
    response = client.get("/health")
    assert response.status_code == 200
