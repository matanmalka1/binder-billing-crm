from datetime import date

from app.businesses.models.business import Business
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from tests.helpers.identity import seed_client_with_business


def _business(db) -> Business:
    _client, business = seed_client_with_business(
        db,
        full_name="Signature Client",
        id_number="999999991",
        email="client@example.com",
        phone="050-1234567",
        business_name="Signature Business",
        opened_at=date(2026, 1, 1),
    )
    db.commit()
    return business


def test_signature_request_full_sign_flow(client, test_db, advisor_headers):
    business = _business(test_db)

    create_resp = client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "Engagement Letter",
            "description": "Please approve",
            "signer_name": "Client Rep",
            "content_to_hash": "hash-me",
        },
    )
    assert create_resp.status_code == 201
    req = create_resp.json()
    assert req["status"] == "draft"
    request_id = req["id"]

    send_resp = client.post(
        f"/api/v1/signature-requests/{request_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    assert send_resp.status_code == 200
    sent = send_resp.json()
    token = sent["signing_token"]
    assert sent["status"] == "pending_signature"
    assert sent["signing_url_hint"] == f"/sign/{token}"

    view_resp = client.get(f"/sign/{token}")
    assert view_resp.status_code == 200
    assert view_resp.json()["status"] == "pending_signature"

    approve_resp = client.post(f"/sign/{token}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "signed"

    detail_resp = client.get(
        f"/api/v1/signature-requests/{request_id}", headers=advisor_headers
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "signed"
    # Audit trail should include created, sent, viewed, signed
    event_types = [e["event_type"] for e in detail["audit_trail"]]
    assert {"created", "sent", "viewed", "signed"} <= set(event_types)


def test_signature_request_decline_records_reason(client, test_db, advisor_headers):
    business = _business(test_db)

    create_resp = client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "Decline Test",
            "signer_name": "Decliner",
        },
    )
    request_id = create_resp.json()["id"]

    send_resp = client.post(
        f"/api/v1/signature-requests/{request_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    token = send_resp.json()["signing_token"]

    decline_resp = client.post(
        f"/sign/{token}/decline",
        json={"reason": "I disagree"},
    )
    assert decline_resp.status_code == 200
    assert decline_resp.json()["status"] == "declined"

    repo = SignatureRequestRepository(test_db)
    stored = repo.get_by_id(request_id)
    assert stored.status.value == "declined"
    assert stored.signing_token is None
    # Decline reason persisted
    assert stored.decline_reason == "I disagree"


def test_send_requires_draft_status(client, test_db, advisor_headers):
    business = _business(test_db)

    create_resp = client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "Send Twice",
            "signer_name": "Signer",
        },
    )
    request_id = create_resp.json()["id"]

    first_send = client.post(
        f"/api/v1/signature-requests/{request_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    assert first_send.status_code == 200

    second_send = client.post(
        f"/api/v1/signature-requests/{request_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    assert second_send.status_code == 400
    assert second_send.json()["error"] == "SIGNATURE_REQUEST.INVALID_STATUS"


def test_list_pending_returns_only_pending(client, test_db, advisor_headers):
    business = _business(test_db)

    # Two pending
    ids = []
    for i in range(2):
        resp = client.post(
            "/api/v1/signature-requests",
            headers=advisor_headers,
            json={
                "business_id": business.id,
                "client_record_id": business.client_id,
                "request_type": "custom",
                "title": f"Pending {i}",
                "signer_name": "Signer",
            },
        )
        req_id = resp.json()["id"]
        client.post(
            f"/api/v1/signature-requests/{req_id}/send",
            headers=advisor_headers,
            json={"expiry_days": 7},
        )
        ids.append(req_id)

    # One draft should not appear
    client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "Draft",
            "signer_name": "Signer",
        },
    )

    pending_resp = client.get(
        "/api/v1/signature-requests/pending?page=1&page_size=10",
        headers=advisor_headers,
    )
    assert pending_resp.status_code == 200
    payload = pending_resp.json()
    assert payload["total"] == 2
    assert all(item["status"] == "pending_signature" for item in payload["items"])


def test_list_active_includes_draft_and_pending(client, test_db, advisor_headers):
    business = _business(test_db)
    ids_by_status = {}

    for title in ("Pending", "Draft"):
        resp = client.post(
            "/api/v1/signature-requests",
            headers=advisor_headers,
            json={
                "business_id": business.id,
                "client_record_id": business.client_id,
                "request_type": "custom",
                "title": title,
                "signer_name": "Signer",
            },
        )
        assert resp.status_code == 201
        ids_by_status[title] = resp.json()["id"]

    client.post(
        f"/api/v1/signature-requests/{ids_by_status['Pending']}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )

    active_resp = client.get(
        "/api/v1/signature-requests/active?page=1&page_size=10",
        headers=advisor_headers,
    )

    assert active_resp.status_code == 200
    payload = active_resp.json()
    assert payload["total"] == 2
    returned = {item["id"]: item["status"] for item in payload["items"]}
    assert returned[ids_by_status["Pending"]] == "pending_signature"
    assert returned[ids_by_status["Draft"]] == "draft"


def test_list_active_excludes_terminal_statuses(client, test_db, advisor_headers):
    business = _business(test_db)

    def _create(title):
        resp = client.post(
            "/api/v1/signature-requests",
            headers=advisor_headers,
            json={
                "business_id": business.id,
                "client_record_id": business.client_id,
                "request_type": "custom",
                "title": title,
                "signer_name": "Signer",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    draft_id = _create("Active Draft")
    cancel_id = _create("To Cancel")

    send_resp = client.post(
        f"/api/v1/signature-requests/{cancel_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    assert send_resp.status_code == 200
    token = send_resp.json()["signing_token"]

    client.post(f"/sign/{token}/decline", json={"reason": "not interested"})

    active_resp = client.get(
        "/api/v1/signature-requests/active?page=1&page_size=50",
        headers=advisor_headers,
    )
    assert active_resp.status_code == 200
    payload = active_resp.json()
    returned_ids = {item["id"] for item in payload["items"]}
    assert draft_id in returned_ids
    assert cancel_id not in returned_ids


def test_list_active_excludes_soft_deleted(client, test_db, advisor_headers):
    business = _business(test_db)

    create_resp = client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "To Delete",
            "signer_name": "Signer",
        },
    )
    assert create_resp.status_code == 201
    req_id = create_resp.json()["id"]

    repo = SignatureRequestRepository(test_db)
    from app.utils.time_utils import utcnow
    repo.update(req_id, deleted_at=utcnow(), deleted_by=1)
    test_db.commit()

    active_resp = client.get(
        "/api/v1/signature-requests/active?page=1&page_size=50",
        headers=advisor_headers,
    )
    assert active_resp.status_code == 200
    returned_ids = {item["id"] for item in active_resp.json()["items"]}
    assert req_id not in returned_ids


def test_invalid_token_returns_error_on_sign(client):
    resp = client.post("/sign/does-not-exist/approve")
    assert resp.status_code == 400
    assert resp.json()["error"] == "SIGNATURE_REQUEST.TOKEN_INVALID"


def test_get_audit_trail_endpoint_returns_events(client, test_db, advisor_headers):
    business = _business(test_db)

    create_resp = client.post(
        "/api/v1/signature-requests",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "client_record_id": business.client_id,
            "request_type": "custom",
            "title": "Audit Trail Endpoint",
            "signer_name": "Signer",
        },
    )
    request_id = create_resp.json()["id"]

    send_resp = client.post(
        f"/api/v1/signature-requests/{request_id}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )
    assert send_resp.status_code == 200

    audit_resp = client.get(
        f"/api/v1/signature-requests/{request_id}/audit-trail",
        headers=advisor_headers,
    )
    assert audit_resp.status_code == 200
    payload = audit_resp.json()
    assert isinstance(payload["items"], list)
    event_types = [e["event_type"] for e in payload["items"]]
    assert {"created", "sent"} <= set(event_types)
