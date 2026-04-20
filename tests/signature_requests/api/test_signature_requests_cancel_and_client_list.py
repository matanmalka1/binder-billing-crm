from datetime import date

from app.businesses.models.business import Business
from app.clients.models.client import Client


def _business(db, suffix: str) -> Business:
    client = Client(
        full_name=f"Signature List Client {suffix}",
        id_number=f"SIG-API-{suffix}",
        email=f"sig{suffix}@example.com",
    )
    db.add(client)
    db.flush()
    business = Business(
        client_id=client.id,
        business_name=f"Signature List Business {suffix}",
        opened_at=date(2026, 1, 1),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _create_signature_request(api_client, headers, business: Business, title: str) -> int:
    resp = api_client.post(
        "/api/v1/signature-requests",
        headers=headers,
        json={
            "business_id": business.id,
            "client_id": business.client_id,
            "request_type": "custom",
            "title": title,
            "signer_name": "Signer",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_cancel_signature_request(client, test_db, advisor_headers):
    business = _business(test_db, "A")
    request_id = _create_signature_request(client, advisor_headers, business, "Cancelable")

    cancel_resp = client.post(
        f"/api/v1/signature-requests/{request_id}/cancel",
        headers=advisor_headers,
        json={"reason": "Client asked to stop"},
    )

    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "canceled"

    detail = client.get(f"/api/v1/signature-requests/{request_id}", headers=advisor_headers)
    assert detail.status_code == 200
    events = [e["event_type"] for e in detail.json()["audit_trail"]]
    assert "canceled" in events


def test_list_signature_requests_by_client_with_status_filter(client, test_db, advisor_headers):
    business_a = _business(test_db, "B")
    business_b = _business(test_db, "C")

    req_a_pending = _create_signature_request(client, advisor_headers, business_a, "Pending A")
    client.post(
        f"/api/v1/signature-requests/{req_a_pending}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )

    req_a_draft = _create_signature_request(client, advisor_headers, business_a, "Draft A")
    _create_signature_request(client, advisor_headers, business_b, "Other client")

    all_resp = client.get(
        f"/api/v1/businesses/{business_a.id}/signature-requests?page=1&page_size=10",
        headers=advisor_headers,
    )
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 2
    returned_ids = {item["id"] for item in all_resp.json()["items"]}
    assert returned_ids == {req_a_pending, req_a_draft}

    pending_resp = client.get(
        f"/api/v1/businesses/{business_a.id}/signature-requests?status=pending_signature",
        headers=advisor_headers,
    )
    assert pending_resp.status_code == 200
    assert pending_resp.json()["total"] == 1
    assert pending_resp.json()["items"][0]["id"] == req_a_pending


def test_get_signature_request_not_found_returns_404(client, advisor_headers):
    resp = client.get("/api/v1/signature-requests/999999", headers=advisor_headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "בקשת החתימה לא נמצאה"
