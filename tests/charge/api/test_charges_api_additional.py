from datetime import date

from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client


def _business(test_db):
    client = Client(
        full_name="Charge API Extra",
        id_number="700000001",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_get_charge_as_advisor_and_delete_paths(client, advisor_headers, test_db):
    business = _business(test_db)
    create = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"business_id": business.id, "amount": 100.0, "charge_type": "consultation_fee"},
    )
    assert create.status_code == 201
    charge_id = create.json()["id"]

    get_adv = client.get(f"/api/v1/charges/{charge_id}", headers=advisor_headers)
    assert get_adv.status_code == 200
    assert "amount" in get_adv.json()

    delete_ok = client.delete(f"/api/v1/charges/{charge_id}", headers=advisor_headers)
    assert delete_ok.status_code == 204

    delete_missing = client.delete("/api/v1/charges/999999", headers=advisor_headers)
    assert delete_missing.status_code == 404


def test_bulk_action_endpoint_and_invalid_period_validation(client, advisor_headers, test_db):
    business = _business(test_db)
    first = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"business_id": business.id, "amount": 40.0, "charge_type": "consultation_fee"},
    )
    second = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"business_id": business.id, "amount": 60.0, "charge_type": "consultation_fee"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    bulk = client.post(
        "/api/v1/charges/bulk-action",
        headers={**advisor_headers, "X-Idempotency-Key": "bulk-charge-test-1"},
        json={"charge_ids": [first.json()["id"], second.json()["id"]], "action": "issue"},
    )
    assert bulk.status_code == 200
    payload = bulk.json()
    assert payload["succeeded"] == [first.json()["id"], second.json()["id"]]
    assert payload["failed"] == []

    invalid_period = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "amount": 10.0,
            "charge_type": "other",
            "period": "2026-13",
        },
    )
    assert invalid_period.status_code == 422


def test_create_charge_supports_bimonthly_period(client, advisor_headers, test_db):
    business = _business(test_db)

    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "amount": 150.0,
            "charge_type": "monthly_retainer",
            "period": "2026-03",
            "months_covered": 2,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["period"] == "2026-03"
    assert payload["months_covered"] == 2
