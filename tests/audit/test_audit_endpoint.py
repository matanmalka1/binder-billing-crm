from datetime import timedelta

from app.audit.constants import ENTITY_CLIENT
from app.audit.services.entity_audit_writer import EntityAuditWriter


def test_audit_endpoint_paginates_and_sorts_newest_first(
    client, test_db, advisor_headers, test_user, create_client_with_business
):
    client_record, _business = create_client_with_business(id_number="AUDIT-001")
    writer = EntityAuditWriter(test_db)
    first = writer.record_update(
        ENTITY_CLIENT, client_record.id, test_user.id, new_value={"step": 1}
    )
    second = writer.record_update(
        ENTITY_CLIENT, client_record.id, test_user.id, new_value={"step": 2}
    )
    third = writer.record_update(
        ENTITY_CLIENT, client_record.id, test_user.id, new_value={"step": 3}
    )
    first.performed_at = third.performed_at - timedelta(minutes=2)
    second.performed_at = third.performed_at - timedelta(minutes=1)
    test_db.commit()

    response = client.get(
        f"/api/v1/audit/client/{client_record.id}?limit=2&offset=1",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert [item["id"] for item in payload["items"]] == [second.id, first.id]
    assert all(item["performed_by_name"] == test_user.full_name for item in payload["items"])


def test_audit_endpoint_limit_validation(client, advisor_headers):
    response = client.get("/api/v1/audit/client/55?limit=201", headers=advisor_headers)

    assert response.status_code == 422


def test_audit_endpoint_rejects_unknown_entity_type(client, advisor_headers):
    response = client.get("/api/v1/audit/not_supported/55", headers=advisor_headers)

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "סוג ישות לא נתמך להיסטוריית שינויים"
    assert payload["error"]["code"] == "AUDIT.INVALID_ENTITY_TYPE"


def test_audit_endpoint_returns_404_for_missing_entity(client, advisor_headers):
    response = client.get("/api/v1/audit/client/999999", headers=advisor_headers)

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["message"] == "הישות המבוקשת לא נמצאה"
    assert payload["error"]["code"] == "AUDIT.ENTITY_NOT_FOUND"
