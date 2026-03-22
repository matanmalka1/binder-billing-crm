from datetime import date

from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client, IdNumberType


def _seed_client_and_business(test_db, *, user_id: int):
    crm_client = Client(
        full_name="Status Client",
        id_number="740000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=user_id,
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)

    business = Business(
        client_id=crm_client.id,
        business_name="Status Biz",
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
        created_by=user_id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return crm_client, business


def test_business_status_card_defaults_are_returned(client, test_db, test_user, advisor_headers):
    crm_client, business = _seed_client_and_business(test_db, user_id=test_user.id)

    response = client.get(f"/api/v1/businesses/{business.id}/status-card?year=2026", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == crm_client.id
    assert data["business_id"] == business.id
    assert data["year"] == 2026

    assert data["vat"]["periods_total"] == 0
    assert data["vat"]["periods_filed"] == 0
    assert data["charges"]["unpaid_count"] == 0
    assert data["documents"]["total_count"] == 0


def test_business_status_card_not_found(client, advisor_headers):
    response = client.get("/api/v1/businesses/999999/status-card", headers=advisor_headers)

    assert response.status_code == 404
    assert response.json()["error"] == "BUSINESS.NOT_FOUND"
