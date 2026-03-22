from app.clients.models import Client


def _client(db, suffix: str) -> Client:
    client = Client(
        full_name=f"Signature List Client {suffix}",
        id_number=f"SIG-API-{suffix}",
        email=f"sig{suffix}@example.com",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _create_signature_request(api_client, headers, client_id: int, title: str) -> int:
    resp = api_client.post(
        "/api/v1/signature-requests",
        headers=headers,
        json={
            "business_id": client_id,
            "request_type": "custom",
            "title": title,
            "signer_name": "Signer",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_cancel_signature_request(client, test_db, advisor_headers):
    crm_client = _client(test_db, "A")
    request_id = _create_signature_request(client, advisor_headers, crm_client.id, "Cancelable")

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
    client_a = _client(test_db, "B")
    client_b = _client(test_db, "C")

    req_a_pending = _create_signature_request(client, advisor_headers, client_a.id, "Pending A")
    client.post(
        f"/api/v1/signature-requests/{req_a_pending}/send",
        headers=advisor_headers,
        json={"expiry_days": 7},
    )

    req_a_draft = _create_signature_request(client, advisor_headers, client_a.id, "Draft A")
    _create_signature_request(client, advisor_headers, client_b.id, "Other client")

    all_resp = client.get(
        f"/api/v1/businesses/{client_a.id}/signature-requests?page=1&page_size=10",
        headers=advisor_headers,
    )
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 2
    returned_ids = {item["id"] for item in all_resp.json()["items"]}
    assert returned_ids == {req_a_pending, req_a_draft}

    pending_resp = client.get(
        f"/api/v1/businesses/{client_a.id}/signature-requests?status=pending_signature",
        headers=advisor_headers,
    )
    assert pending_resp.status_code == 200
    assert pending_resp.json()["total"] == 1
    assert pending_resp.json()["items"][0]["id"] == req_a_pending
