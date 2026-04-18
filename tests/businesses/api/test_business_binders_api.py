from datetime import date

from app.binders.models.binder import Binder
from app.businesses.models.business import Business
from app.clients.models.client import Client, IdNumberType


def _seed_client_business_and_binder(test_db, *, user_id: int):
    crm_client = Client(
        full_name="Binders Client",
        id_number="720000001",
        id_number_type=IdNumberType.CORPORATION,
        created_by=user_id,
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)

    business = Business(
        client_id=crm_client.id,
        business_name="Binders Biz",
        opened_at=date(2025, 1, 1),
        created_by=user_id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)

    binder = Binder(
        client_id=crm_client.id,
        binder_number="BIZ-BIND-001",
        period_start=date(2026, 1, 1),
        created_by=user_id,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    return business, binder


def test_list_business_binders_returns_client_binders(client, test_db, test_user, advisor_headers):
    business, binder = _seed_client_business_and_binder(test_db, user_id=test_user.id)

    response = client.get(
        f"/api/v1/clients/{business.client_id}/binders?page=1&page_size=20",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == binder.id
    assert data["items"][0]["client_id"] == business.client_id
    assert data["items"][0]["binder_number"] == "BIZ-BIND-001"


def test_list_business_binders_business_not_found(client, advisor_headers):
    response = client.get(
        "/api/v1/clients/999999/binders?page=1&page_size=20",
        headers=advisor_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"] == "CLIENT.NOT_FOUND"
