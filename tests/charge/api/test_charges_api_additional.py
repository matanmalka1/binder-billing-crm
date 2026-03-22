from datetime import date

from app.businesses.models.business import Business, BusinessType
from app.clients.models import Client


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
        business_type=BusinessType.COMPANY,
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
