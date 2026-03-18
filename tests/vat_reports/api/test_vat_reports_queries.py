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
        json={"client_id": vat_client.id, "period": "2026-08", "assigned_to": assignee.id},
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
        json={"filing_method": "online"},
    )
    assert file_resp.status_code == 200

    get_resp = client.get(f"/api/v1/vat/work-items/{item_id}", headers=advisor_headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == item_id
    assert body["assigned_to_name"] == "VAT Assignee"
    assert body["filed_by_name"] == test_user.full_name
    assert body["submission_deadline"] == "2026-09-15"
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
        json={"filing_method": "online"},
    ).status_code == 200

    list_resp = client.get(
        f"/api/v1/vat/work-items?status=filed&client_name={vat_client.full_name}",
        headers=advisor_headers,
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == filed_item_id
    assert body["items"][0]["status"] == "filed"
    assert body["items"][0]["client_name"] == vat_client.full_name
    assert body["items"][0]["id"] != pending_item_id
