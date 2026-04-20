from datetime import date

from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import IdNumberType


def _business(db) -> Business:
    crm_client = Client(full_name="Advance Gen API Client", id_number="APGAPI001")
    db.add(crm_client)
    db.flush()
    legal_entity = LegalEntity(id_number="APGAPI001", id_number_type=IdNumberType.INDIVIDUAL)
    db.add(legal_entity)
    db.flush()
    db.commit()
    db.refresh(crm_client)

    business = Business(
        client_id=crm_client.id,
        legal_entity_id=legal_entity.id,
        business_name="Advance Gen Business",
        opened_at=date.today(),
    )
    db.add(business)
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
