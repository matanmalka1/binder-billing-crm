from datetime import date

from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client


def _business(db) -> Business:
    crm_client = Client(full_name="Advance Gen API Client", id_number="APGAPI001")
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)

    business = Business(
        client_id=crm_client.id,
        business_name="Advance Gen Business",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_generate_schedule_endpoint_returns_counts(client, test_db, advisor_headers):
    business = _business(test_db)

    resp = client.post(
        "/api/v1/advance-payments/generate",
        headers=advisor_headers,
        json={"business_id": business.id, "year": 2026},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] == 12
    assert payload["skipped"] == 0


def test_generate_schedule_endpoint_is_advisor_only(client, test_db, secretary_headers):
    business = _business(test_db)

    resp = client.post(
        "/api/v1/advance-payments/generate",
        headers=secretary_headers,
        json={"business_id": business.id, "year": 2026},
    )

    assert resp.status_code == 403
