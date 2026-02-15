from datetime import date

from app.models import Client, ClientType


def _seed_client(test_db, id_number: str) -> Client:
    test_client = Client(
        full_name="Test Client",
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)
    return test_client


def test_binder_status_change_creates_log(client, auth_token, test_db, test_user):
    """Test that binder status changes create audit logs."""
    test_client = _seed_client(test_db, "111222333")

    # Receive binder
    response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_id": test_client.id,
            "binder_number": "BND-2026-001",
            "received_at": "2026-02-08",
            "received_by": test_user.id,
            "notes": "Test binder",
        },
    )

    assert response.status_code == 201
    binder_data = response.json()
    binder_id = binder_data["id"]
    actions = binder_data.get("available_actions", [])
    assert any(action["key"] == "ready" for action in actions)
    ready_action = next(action for action in actions if action["key"] == "ready")
    assert ready_action["id"] == f"binder-{binder_id}-ready"

    # Verify status log was created
    from app.repositories import BinderStatusLogRepository

    log_repo = BinderStatusLogRepository(test_db)
    logs = log_repo.list_by_binder(binder_id)

    assert len(logs) == 1
    assert logs[0].old_status == "null"
    assert logs[0].new_status == "in_office"
    assert logs[0].changed_by == test_user.id


def test_binder_ready_endpoint_and_return_accepts_empty_body(
    client,
    auth_token,
    test_db,
    test_user,
):
    """Test /ready route and optional body support on /return."""
    test_client = _seed_client(test_db, "444555666")

    receive_response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_id": test_client.id,
            "binder_number": "BND-2026-002",
            "received_at": "2026-02-08",
            "received_by": test_user.id,
        },
    )
    assert receive_response.status_code == 201
    binder_id = receive_response.json()["id"]

    ready_response = client.post(
        f"/api/v1/binders/{binder_id}/ready",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert ready_response.status_code == 200
    ready_data = ready_response.json()
    assert ready_data["status"] == "ready_for_pickup"
    ready_actions = ready_data.get("available_actions", [])
    assert any(action["key"] == "return" for action in ready_actions)
    return_action = next(action for action in ready_actions if action["key"] == "return")
    assert return_action["id"] == f"binder-{binder_id}-return"
    assert return_action["confirm"] is not None
    assert return_action["confirm"]["title"] == "אישור החזרת תיק"

    return_response = client.post(
        f"/api/v1/binders/{binder_id}/return",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={},
    )

    assert return_response.status_code == 200
    returned_data = return_response.json()
    assert returned_data["status"] == "returned"

    from app.repositories import BinderStatusLogRepository

    log_repo = BinderStatusLogRepository(test_db)
    logs = log_repo.list_by_binder(binder_id)

    # Should have: intake, mark ready, return
    assert len(logs) >= 3
    assert logs[-1].new_status == "returned"


def test_binder_list_includes_available_actions(client, auth_token, test_db, test_user):
    """List endpoint includes action tokens per binder."""
    test_client = _seed_client(test_db, "777888999")

    client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_id": test_client.id,
            "binder_number": "BND-2026-003",
            "received_at": "2026-02-08",
            "received_by": test_user.id,
        },
    )

    list_response = client.get(
        "/api/v1/binders",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert "available_actions" in data["items"][0]
