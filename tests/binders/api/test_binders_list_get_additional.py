from datetime import date

from app.clients.models import Client, ClientType


def _create_client(test_db, suffix: str) -> Client:
    crm_client = Client(
        full_name=f"Binders List Client {suffix}",
        id_number=f"BDL{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)
    return crm_client


def _create_binder_via_api(client, advisor_headers, crm_client_id: int, user_id: int) -> int:
    res = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": crm_client_id,
            "binder_number": "BDL-001",
            "binder_type": "other",
            "received_at": date.today().isoformat(),
            "received_by": user_id,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_get_and_delete_binder_paths(client, test_db, advisor_headers, test_user):
    crm_client = _create_client(test_db, "1")
    binder_id = _create_binder_via_api(client, advisor_headers, crm_client.id, test_user.id)

    get_ok = client.get(f"/api/v1/binders/{binder_id}", headers=advisor_headers)
    assert get_ok.status_code == 200
    assert get_ok.json()["id"] == binder_id

    get_missing = client.get("/api/v1/binders/999999", headers=advisor_headers)
    assert get_missing.status_code == 404

    del_ok = client.delete(f"/api/v1/binders/{binder_id}", headers=advisor_headers)
    assert del_ok.status_code == 204

    del_missing = client.delete("/api/v1/binders/999999", headers=advisor_headers)
    assert del_missing.status_code == 404


def test_receive_allows_reusing_number_after_soft_delete(client, test_db, advisor_headers, test_user):
    crm_client = _create_client(test_db, "2")

    first_id = _create_binder_via_api(client, advisor_headers, crm_client.id, test_user.id)
    del_ok = client.delete(f"/api/v1/binders/{first_id}", headers=advisor_headers)
    assert del_ok.status_code == 204

    second = client.post(
        "/api/v1/binders/receive",
        headers=advisor_headers,
        json={
            "client_id": crm_client.id,
            "binder_number": "BDL-001",
            "binder_type": "other",
            "received_at": date.today().isoformat(),
            "received_by": test_user.id,
        },
    )
    assert second.status_code == 201
    assert second.json()["id"] != first_id
