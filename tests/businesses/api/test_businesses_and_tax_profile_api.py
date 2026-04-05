from datetime import date

from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.clients.models.client import Client, IdNumberType


def _create_client(test_db, *, user_id: int, name: str, id_number: str) -> Client:
    crm_client = Client(
        full_name=name,
        id_number=id_number,
        id_number_type=IdNumberType.CORPORATION,
        created_by=user_id,
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)
    return crm_client


def _create_business(test_db, *, client_id: int, user_id: int, name: str) -> Business:
    business = Business(
        client_id=client_id,
        business_name=name,
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
        created_by=user_id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_create_list_and_get_business_endpoints(client, test_db, test_user, advisor_headers, secretary_headers):
    crm_client = _create_client(
        test_db,
        user_id=test_user.id,
        name="API Client A",
        id_number="710001001",
    )

    create_payload = {
        "business_type": "company",
        "opened_at": "2026-01-01",
        "business_name": "API Biz A",
        "notes": "hello",
    }
    created_resp = client.post(
        f"/api/v1/clients/{crm_client.id}/businesses",
        headers=advisor_headers,
        json=create_payload,
    )
    assert created_resp.status_code == 201
    created_data = created_resp.json()
    assert created_data["client_id"] == crm_client.id
    assert created_data["business_name"] == "API Biz A"
    assert created_data["available_actions"][0]["key"] == "freeze"

    list_client_resp = client.get(
        f"/api/v1/clients/{crm_client.id}/businesses?page=1&page_size=10",
        headers=secretary_headers,
    )
    assert list_client_resp.status_code == 200
    list_client_data = list_client_resp.json()
    assert list_client_data["total"] == 2
    assert created_data["id"] in [item["id"] for item in list_client_data["items"]]
    created_row = next(item for item in list_client_data["items"] if item["id"] == created_data["id"])
    assert created_row["available_actions"] == []

    list_all_resp = client.get(
        "/api/v1/businesses?page=1&page_size=10&search=API Biz",
        headers=advisor_headers,
    )
    assert list_all_resp.status_code == 200
    list_all_data = list_all_resp.json()
    assert list_all_data["total"] == 1
    assert list_all_data["items"][0]["client_full_name"] == "API Client A"
    assert list_all_data["items"][0]["client_id_number"] == "710001001"

    business_id = created_data["id"]
    get_resp = client.get(f"/api/v1/businesses/{business_id}", headers=secretary_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["available_actions"] == []


def test_update_delete_restore_and_bulk_action_endpoints(
    client,
    test_db,
    test_user,
    advisor_headers,
    secretary_headers,
):
    crm_client = _create_client(
        test_db,
        user_id=test_user.id,
        name="API Client B",
        id_number="710001002",
    )
    business_a = _create_business(test_db, client_id=crm_client.id, user_id=test_user.id, name="Biz A")
    business_b = _create_business(test_db, client_id=crm_client.id, user_id=test_user.id, name="Biz B")
    business_c = _create_business(test_db, client_id=crm_client.id, user_id=test_user.id, name="Biz C")

    freeze_forbidden = client.patch(
        f"/api/v1/businesses/{business_a.id}",
        headers=secretary_headers,
        json={"status": "frozen"},
    )
    assert freeze_forbidden.status_code == 403
    assert freeze_forbidden.json()["error"] == "BUSINESS.FORBIDDEN"

    freeze_ok = client.patch(
        f"/api/v1/businesses/{business_a.id}",
        headers=advisor_headers,
        json={"status": "frozen", "notes": "manual"},
    )
    assert freeze_ok.status_code == 200
    assert freeze_ok.json()["status"] == "frozen"
    assert freeze_ok.json()["notes"] == "manual"

    delete_forbidden = client.delete(f"/api/v1/businesses/{business_b.id}", headers=secretary_headers)
    assert delete_forbidden.status_code == 403

    delete_ok = client.delete(f"/api/v1/businesses/{business_b.id}", headers=advisor_headers)
    assert delete_ok.status_code == 204

    get_deleted = client.get(f"/api/v1/businesses/{business_b.id}", headers=advisor_headers)
    assert get_deleted.status_code == 404
    assert get_deleted.json()["error"] == "BUSINESS.NOT_FOUND"

    restore_ok = client.post(f"/api/v1/businesses/{business_b.id}/restore", headers=advisor_headers)
    assert restore_ok.status_code == 200
    assert restore_ok.json()["status"] == "active"


def test_business_tax_profile_api_endpoints(client, test_db, test_user, advisor_headers, secretary_headers):
    crm_client = _create_client(
        test_db,
        user_id=test_user.id,
        name="API Client C",
        id_number="710001003",
    )
    business = _create_business(test_db, client_id=crm_client.id, user_id=test_user.id, name="Tax Biz")

    get_empty = client.get(f"/api/v1/businesses/{business.id}/tax-profile", headers=secretary_headers)
    assert get_empty.status_code == 200
    empty_data = get_empty.json()
    assert empty_data["business_id"] == business.id
    assert empty_data["vat_type"] is None
    assert empty_data["fiscal_year_start_month"] == 1

    update_forbidden = client.patch(
        f"/api/v1/businesses/{business.id}/tax-profile",
        headers=secretary_headers,
        json={"vat_type": "exempt"},
    )
    assert update_forbidden.status_code == 403

    update_ok = client.patch(
        f"/api/v1/businesses/{business.id}/tax-profile",
        headers=advisor_headers,
        json={
            "vat_type": "exempt",
            "accountant_name": "Dana",
            "advance_rate": "8.25",
            "fiscal_year_start_month": 4,
        },
    )
    assert update_ok.status_code == 200
    updated = update_ok.json()
    assert updated["business_id"] == business.id
    assert updated["vat_type"] == "exempt"
    assert updated["accountant_name"] == "Dana"
    assert updated["advance_rate"] == "8.25"
    assert updated["fiscal_year_start_month"] == 4

    get_updated = client.get(f"/api/v1/businesses/{business.id}/tax-profile", headers=advisor_headers)
    assert get_updated.status_code == 200
    assert get_updated.json()["vat_type"] == "exempt"

    missing = client.get("/api/v1/businesses/999999/tax-profile", headers=advisor_headers)
    assert missing.status_code == 404
    assert missing.json()["error"] == "BUSINESS.NOT_FOUND"
