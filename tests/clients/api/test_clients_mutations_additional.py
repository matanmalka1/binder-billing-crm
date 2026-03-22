from app.clients.models.client import IdNumberType
from app.clients.repositories.client_repository import ClientRepository


def _create_client(client, headers, *, full_name="Client A", id_number="700000001"):
    return client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "full_name": full_name,
            "id_number": id_number,
            "id_number_type": "corporation",
        },
    )


def test_get_and_patch_client(client, advisor_headers):
    created = _create_client(client, advisor_headers, id_number="700000011")
    client_id = created.json()["id"]

    fetched = client.get(f"/api/v1/clients/{client_id}", headers=advisor_headers)
    assert fetched.status_code == 200
    assert fetched.json()["full_name"] == "Client A"

    updated = client.patch(
        f"/api/v1/clients/{client_id}",
        headers=advisor_headers,
        json={"full_name": "Client B", "phone": "0501234567"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Client B"
    assert updated.json()["phone"] == "0501234567"


def test_get_client_not_found_returns_domain_error(client, advisor_headers):
    response = client.get("/api/v1/clients/99999", headers=advisor_headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "CLIENT.NOT_FOUND"


def test_delete_and_restore_client_role_rules(client, advisor_headers, secretary_headers):
    created = _create_client(client, advisor_headers, id_number="700000021")
    client_id = created.json()["id"]

    denied = client.delete(f"/api/v1/clients/{client_id}", headers=secretary_headers)
    assert denied.status_code == 403

    deleted = client.delete(f"/api/v1/clients/{client_id}", headers=advisor_headers)
    assert deleted.status_code == 204

    missing_after_delete = client.get(f"/api/v1/clients/{client_id}", headers=advisor_headers)
    assert missing_after_delete.status_code == 404

    restore_denied = client.post(f"/api/v1/clients/{client_id}/restore", headers=secretary_headers)
    assert restore_denied.status_code == 403

    restored = client.post(f"/api/v1/clients/{client_id}/restore", headers=advisor_headers)
    assert restored.status_code == 200
    assert restored.json()["id"] == client_id


def test_restore_conflict_when_active_duplicate_exists(client, advisor_headers, test_db):
    first = _create_client(client, advisor_headers, full_name="Old One", id_number="700000031")
    first_id = first.json()["id"]

    client.delete(f"/api/v1/clients/{first_id}", headers=advisor_headers)
    # Seed an active duplicate directly at repository level so restore can hit CLIENT.CONFLICT.
    ClientRepository(test_db).create(
        full_name="Active One",
        id_number="700000031",
        id_number_type=IdNumberType.CORPORATION,
        created_by=1,
    )

    restored = client.post(f"/api/v1/clients/{first_id}/restore", headers=advisor_headers)

    assert restored.status_code == 409
    assert restored.json()["error"] == "CLIENT.CONFLICT"


def test_create_returns_deleted_exists_conflict_payload(client, advisor_headers):
    first = _create_client(client, advisor_headers, full_name="Deleted Source", id_number="700000032")
    first_id = first.json()["id"]
    client.delete(f"/api/v1/clients/{first_id}", headers=advisor_headers)

    duplicate = _create_client(client, advisor_headers, full_name="Try Again", id_number="700000032")

    assert duplicate.status_code == 409
    payload = duplicate.json()["detail"]
    assert payload["error"] == "CLIENT.DELETED_EXISTS"
    assert payload["conflict"]["id_number"] == "700000032"
    assert len(payload["conflict"]["deleted_clients"]) == 1


def test_conflict_endpoint_includes_active_and_deleted(client, advisor_headers):
    active = _create_client(client, advisor_headers, full_name="Conflict Active", id_number="700000041")
    deleted = _create_client(client, advisor_headers, full_name="Conflict Deleted", id_number="700000042")

    client.delete(f"/api/v1/clients/{deleted.json()['id']}", headers=advisor_headers)

    active_info = client.get("/api/v1/clients/conflict/700000041", headers=advisor_headers)
    assert active_info.status_code == 200
    body_active = active_info.json()
    assert len(body_active["active_clients"]) == 1
    assert len(body_active["deleted_clients"]) == 0

    deleted_info = client.get("/api/v1/clients/conflict/700000042", headers=advisor_headers)
    assert deleted_info.status_code == 200
    body_deleted = deleted_info.json()
    assert len(body_deleted["active_clients"]) == 0
    assert len(body_deleted["deleted_clients"]) == 1


def test_create_conflict_payload_contains_conflict_lists(client, advisor_headers):
    _create_client(client, advisor_headers, full_name="First", id_number="700000051")

    duplicate = _create_client(client, advisor_headers, full_name="Second", id_number="700000051")

    assert duplicate.status_code == 409
    payload = duplicate.json()["detail"]
    assert payload["error"] == "CLIENT.CONFLICT"
    assert payload["conflict"]["id_number"] == "700000051"
    assert len(payload["conflict"]["active_clients"]) == 1


def test_create_validates_israeli_checksum_for_individual(client, advisor_headers):
    response = client.post(
        "/api/v1/clients",
        headers=advisor_headers,
        json={
            "full_name": "Checksum Invalid",
            "id_number": "123456789",
            "id_number_type": "individual",
        },
    )

    assert response.status_code == 422


def test_list_clients_respects_search_and_pagination(client, advisor_headers):
    _create_client(client, advisor_headers, full_name="Alpha Client", id_number="700000061")
    _create_client(client, advisor_headers, full_name="Beta Client", id_number="700000062")

    response = client.get(
        "/api/v1/clients?search=Alpha&page=1&page_size=1",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["full_name"] == "Alpha Client"
