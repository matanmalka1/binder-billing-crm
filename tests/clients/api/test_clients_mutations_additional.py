from datetime import date

from app.clients.models import Client, ClientType


def _create_client(client, advisor_headers):
    resp = client.post(
        "/api/v1/clients",
        headers=advisor_headers,
        json={
            "full_name": "Mutations Client",
            "id_number": "CLMUT001",
            "client_type": "company",
            "opened_at": date.today().isoformat(),
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_get_client_not_found_returns_404(client, advisor_headers):
    resp = client.get("/api/v1/clients/999999", headers=advisor_headers)
    assert resp.status_code == 404


def test_update_delete_and_bulk_action_endpoints(client, advisor_headers):
    client_id = _create_client(client, advisor_headers)

    patch_resp = client.patch(
        f"/api/v1/clients/{client_id}",
        headers=advisor_headers,
        json={"notes": "updated notes"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["notes"] == "updated notes"

    bulk_resp = client.post(
        "/api/v1/clients/bulk-action",
        headers=advisor_headers,
        json={"client_ids": [client_id, 999999], "action": "freeze"},
    )
    assert bulk_resp.status_code == 200
    payload = bulk_resp.json()
    assert client_id in payload["succeeded"]
    assert any(item["id"] == 999999 for item in payload["failed"])

    del_resp = client.delete(f"/api/v1/clients/{client_id}", headers=advisor_headers)
    assert del_resp.status_code == 204

    del_missing = client.delete("/api/v1/clients/999999", headers=advisor_headers)
    assert del_missing.status_code == 404
