from app.businesses.models.business import Business
from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from tests.vat_reports.api.test_vat_reports_utils import create_work_item, income_payload


def _create_user(test_db, email: str, full_name: str, role: UserRole) -> User:
    user = User(
        full_name=full_name,
        email=email,
        password_hash=AuthService.hash_password("pass"),
        role=role,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business_for_client(test_db, client_id: int) -> Business:
    return test_db.query(Business).filter(Business.client_id == client_id).first()


def test_get_work_item_includes_user_names_and_deadline_fields(
    client, test_db, advisor_headers, vat_client, test_user
):
    assignee = _create_user(
        test_db,
        email="vat.assignee@example.com",
        full_name="VAT Assignee",
        role=UserRole.SECRETARY,
    )

    create_resp = client.post(
        "/api/v1/vat/work-items",
        headers=advisor_headers,
        json={"business_id": vat_client.id, "period": "2026-08", "assigned_to": assignee.id},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    add_resp = client.post(
        f"/api/v1/vat/work-items/{item_id}/invoices",
        headers=advisor_headers,
        json=income_payload(invoice_number="INV-QRY-1"),
    )
    assert add_resp.status_code == 201

    ready_resp = client.post(
        f"/api/v1/vat/work-items/{item_id}/ready-for-review",
        headers=advisor_headers,
    )
    assert ready_resp.status_code == 200

    file_resp = client.post(
        f"/api/v1/vat/work-items/{item_id}/file",
        headers=advisor_headers,
        json={"submission_method": "online"},
    )
    assert file_resp.status_code == 200

    get_resp = client.get(f"/api/v1/vat/work-items/{item_id}", headers=advisor_headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == item_id
    assert body["assigned_to_name"] == "VAT Assignee"
    assert body["filed_by_name"] == test_user.full_name
    assert body["submission_deadline"] == "2026-09-19"
    assert isinstance(body["days_until_deadline"], int)
    assert isinstance(body["is_overdue"], bool)


def test_list_work_items_supports_status_and_client_name_filters(
    client, advisor_headers, vat_client
):
    filed_item_id = create_work_item(client, advisor_headers, vat_client, "2026-09")
    pending_item_id = create_work_item(client, advisor_headers, vat_client, "2026-10")

    add_resp = client.post(
        f"/api/v1/vat/work-items/{filed_item_id}/invoices",
        headers=advisor_headers,
        json=income_payload(invoice_number="INV-QRY-2"),
    )
    assert add_resp.status_code == 201
    assert client.post(
        f"/api/v1/vat/work-items/{filed_item_id}/ready-for-review",
        headers=advisor_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/vat/work-items/{filed_item_id}/file",
        headers=advisor_headers,
        json={"submission_method": "online"},
    ).status_code == 200

    list_resp = client.get(
        f"/api/v1/vat/work-items?status=filed&business_name={vat_client.full_name}",
        headers=advisor_headers,
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == filed_item_id
    assert body["items"][0]["status"] == "filed"
    assert body["items"][0]["business_name"] == vat_client.full_name
    assert body["items"][0]["id"] != pending_item_id


def test_list_work_items_supports_filter_by_client_and_tax_identifiers(
    client, advisor_headers, vat_client, test_db
):
    business = _business_for_client(test_db, vat_client.id)
    assert business is not None
    business.tax_id_number = "514123456"
    test_db.commit()

    target_item_id = create_work_item(client, advisor_headers, vat_client, "2026-11")
    _ = create_work_item(client, advisor_headers, vat_client, "2026-12")

    by_client_id = client.get(
        f"/api/v1/vat/work-items?business_name={vat_client.id}",
        headers=advisor_headers,
    )
    assert by_client_id.status_code == 200
    payload_client_id = by_client_id.json()
    assert payload_client_id["total"] >= 1
    assert any(item["id"] == target_item_id for item in payload_client_id["items"])

    by_tax_id = client.get(
        "/api/v1/vat/work-items?business_name=514123456",
        headers=advisor_headers,
    )
    assert by_tax_id.status_code == 200
    payload_tax_id = by_tax_id.json()
    assert payload_tax_id["total"] >= 1
    assert any(item["id"] == target_item_id for item in payload_tax_id["items"])


def test_period_options_default_monthly_returns_12_periods(
    client, advisor_headers, vat_client, test_db
):
    business = _business_for_client(test_db, vat_client.id)
    assert business is not None

    resp = client.get(
        f"/api/v1/vat/businesses/{business.id}/period-options?year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_type"] == "monthly"
    assert len(body["options"]) == 12
    assert body["options"][0]["period"] == "2026-01"
    assert body["options"][0]["label"] == "2026-01"
    assert body["options"][1]["period"] == "2026-02"
    assert body["options"][11]["period"] == "2026-12"
    assert all(not option["is_opened"] for option in body["options"])


def test_period_options_bimonthly_uses_odd_months_and_marks_opened(
    client, advisor_headers, vat_client, test_db
):
    business = _business_for_client(test_db, vat_client.id)
    assert business is not None

    profile = BusinessTaxProfile(business_id=business.id, vat_type=VatType.BIMONTHLY)
    test_db.add(profile)
    test_db.commit()

    create_resp = client.post(
        "/api/v1/vat/work-items",
        headers=advisor_headers,
        json={"business_id": business.id, "period": "2026-03"},
    )
    assert create_resp.status_code == 201

    resp = client.get(
        f"/api/v1/vat/businesses/{business.id}/period-options?year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_type"] == "bimonthly"
    periods = [option["period"] for option in body["options"]]
    assert periods == ["2026-01", "2026-03", "2026-05", "2026-07", "2026-09", "2026-11"]
    labels = [option["label"] for option in body["options"]]
    assert labels[0] == "2026-01/2026-02"
    assert labels[1] == "2026-03/2026-04"
    opened = {option["period"]: option["is_opened"] for option in body["options"]}
    assert opened["2026-03"] is True
    assert opened["2026-01"] is False
