from datetime import date

from app.businesses.models.business import Business
from tests.helpers.identity import seed_business, seed_client_identity


def _business(db) -> Business:
    crm_client = seed_client_identity(
        db,
        full_name="Advance Gen API Client",
        id_number="APGAPI001",
    )
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name="Advance Gen Business",
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_record_id = crm_client.id
    return business


def test_generate_schedule_endpoint_returns_counts(client, test_db, advisor_headers):
    business = _business(test_db)

    resp = client.post(
        f"/api/v1/clients/{business.client_record_id}/advance-payments/generate",
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
        f"/api/v1/clients/{business.client_record_id}/advance-payments/generate",
        headers=secretary_headers,
        json={"business_id": business.id, "year": 2026},
    )

    assert resp.status_code == 403
