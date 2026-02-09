from datetime import date

from app.models import Client, ClientType


def _create_client(test_db) -> Client:
    client = Client(
        full_name="Client B",
        id_number="222222222",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def _create_charge_via_api(client, advisor_headers, client_id: int) -> int:
    res = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"client_id": client_id, "amount": 120.0, "charge_type": "one_time"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_charge_lifecycle_draft_to_issued_to_paid(client, advisor_headers, test_db):
    c = _create_client(test_db)
    charge_id = _create_charge_via_api(client, advisor_headers, c.id)

    issue_res = client.post(f"/api/v1/charges/{charge_id}/issue", headers=advisor_headers)
    assert issue_res.status_code == 200
    issued = issue_res.json()
    assert issued["status"] == "issued"
    assert issued["issued_at"] is not None
    assert issued["paid_at"] is None

    paid_res = client.post(
        f"/api/v1/charges/{charge_id}/mark-paid", headers=advisor_headers
    )
    assert paid_res.status_code == 200
    paid = paid_res.json()
    assert paid["status"] == "paid"
    assert paid["paid_at"] is not None


def test_charge_lifecycle_issued_to_canceled(client, advisor_headers, test_db):
    c = _create_client(test_db)
    charge_id = _create_charge_via_api(client, advisor_headers, c.id)
    assert client.post(f"/api/v1/charges/{charge_id}/issue", headers=advisor_headers).status_code == 200

    cancel_res = client.post(f"/api/v1/charges/{charge_id}/cancel", headers=advisor_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "canceled"


def test_invalid_transitions_return_400(client, advisor_headers, test_db):
    c = _create_client(test_db)
    charge_id = _create_charge_via_api(client, advisor_headers, c.id)

    pay_draft = client.post(f"/api/v1/charges/{charge_id}/mark-paid", headers=advisor_headers)
    assert pay_draft.status_code == 400
    assert "draft" in pay_draft.json()["detail"]

    assert client.post(f"/api/v1/charges/{charge_id}/cancel", headers=advisor_headers).status_code == 200
    issue_canceled = client.post(f"/api/v1/charges/{charge_id}/issue", headers=advisor_headers)
    assert issue_canceled.status_code == 400
    assert "canceled" in issue_canceled.json()["detail"]

    charge_id_2 = _create_charge_via_api(client, advisor_headers, c.id)
    assert client.post(f"/api/v1/charges/{charge_id_2}/issue", headers=advisor_headers).status_code == 200
    assert client.post(f"/api/v1/charges/{charge_id_2}/mark-paid", headers=advisor_headers).status_code == 200
    cancel_paid = client.post(f"/api/v1/charges/{charge_id_2}/cancel", headers=advisor_headers)
    assert cancel_paid.status_code == 400
    assert "paid" in cancel_paid.json()["detail"].lower()


def test_charge_not_found_responses(client, advisor_headers, test_db):
    assert client.get("/api/v1/charges/9999", headers=advisor_headers).status_code == 404
    issue_missing = client.post("/api/v1/charges/9999/issue", headers=advisor_headers)
    assert issue_missing.status_code == 400
    assert "not found" in issue_missing.json()["detail"].lower()

