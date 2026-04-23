from datetime import date

from tests.helpers.identity import SeededClient, seed_client_identity


def _seed_client(test_db, id_number: str, office_client_number: int) -> SeededClient:
    return seed_client_identity(
        test_db,
        full_name="Test Client",
        id_number=id_number,
        office_client_number=office_client_number,
    )


def _receive_payload(payload: dict) -> dict:
    # /binders/receive now returns BinderReceiveResult with nested binder data.
    return payload["binder"] if "binder" in payload else payload


def _receive_request(client_record_id: int, received_by: int, received_at: str = "2026-02-08") -> dict:
    return {
        "client_record_id": client_record_id,
        "received_at": received_at,
        "received_by": received_by,
        "materials": [
            {
                "material_type": "other",
                "period_year": 2026,
                "period_month_start": 2,
                "period_month_end": 2,
                "description": "Test material",
            }
        ],
    }


def test_binder_status_change_creates_log(client, auth_token, test_db, test_user):
    """Test that binder status changes create audit logs."""
    test_client = _seed_client(test_db, "111222333", office_client_number=101)

    # Receive binder
    response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={**_receive_request(test_client.id, test_user.id), "notes": "Test binder"},
    )

    assert response.status_code == 201
    binder_data = _receive_payload(response.json())
    binder_id = binder_data["id"]
    assert binder_data["binder_number"] == "101/1"
    assert binder_data["period_start"] == "2026-02-01"
    actions = binder_data.get("available_actions", [])
    assert any(action["key"] == "ready" for action in actions)
    ready_action = next(action for action in actions if action["key"] == "ready")
    assert ready_action["id"] == f"binder-{binder_id}-ready"
    assert ready_action["confirm"] is not None
    assert ready_action["confirm"]["title"] == "אישור סימון כמוכן לאיסוף"

    # Verify status log was created
    from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository

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
    test_client = _seed_client(test_db, "444555666", office_client_number=102)

    receive_response = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=_receive_request(test_client.id, test_user.id),
    )
    assert receive_response.status_code == 201
    binder_id = _receive_payload(receive_response.json())["id"]

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
    assert return_action["confirm"]["title"] == "אישור החזרת קלסר"

    return_response = client.post(
        f"/api/v1/binders/{binder_id}/return",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={},
    )

    assert return_response.status_code == 200
    returned_data = return_response.json()
    assert returned_data["status"] == "returned"

    from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository

    log_repo = BinderStatusLogRepository(test_db)
    logs = log_repo.list_by_binder(binder_id)

    # Should have: intake, mark ready, return
    assert len(logs) >= 3
    assert logs[-1].new_status == "returned"


def test_binder_list_includes_available_actions(client, auth_token, test_db, test_user):
    """List endpoint includes action tokens per binder."""
    test_client = _seed_client(test_db, "777888999", office_client_number=103)

    client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json=_receive_request(test_client.id, test_user.id),
    )

    list_response = client.get(
        "/api/v1/binders",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert "items" in data
    assert "counters" in data
    assert len(data["items"]) >= 1
    assert "available_actions" in data["items"][0]
    assert set(data["counters"]) == {
        "total",
        "in_office",
        "closed_in_office",
        "archived_in_office",
        "ready_for_pickup",
        "returned",
    }


def test_mark_ready_bulk_marks_closed_and_open_binders_up_to_cutoff(
    client,
    auth_token,
    test_db,
    test_user,
):
    test_client = _seed_client(test_db, "999000111", office_client_number=104)

    first_receive = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_record_id": test_client.id,
            "received_at": "2026-02-08",
            "received_by": test_user.id,
            "materials": [
                {
                    "material_type": "other",
                    "period_year": 2026,
                    "period_month_start": 2,
                    "period_month_end": 2,
                }
            ],
        },
    )
    assert first_receive.status_code == 201
    first_binder_id = first_receive.json()["binder"]["id"]

    second_receive = client.post(
        "/api/v1/binders/receive",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_record_id": test_client.id,
            "received_at": "2026-03-10",
            "received_by": test_user.id,
            "open_new_binder": True,
            "materials": [
                {
                    "material_type": "other",
                    "period_year": 2026,
                    "period_month_start": 3,
                    "period_month_end": 3,
                }
            ],
        },
    )
    assert second_receive.status_code == 201
    second_binder_id = second_receive.json()["binder"]["id"]

    bulk_ready = client.post(
        "/api/v1/binders/mark-ready-bulk",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "client_record_id": test_client.id,
            "until_period_year": 2026,
            "until_period_month": 2,
        },
    )

    assert bulk_ready.status_code == 200
    data = bulk_ready.json()
    assert [binder["id"] for binder in data] == [first_binder_id]
    assert data[0]["status"] == "ready_for_pickup"

    binders = client.get(
        f"/api/v1/binders?client_record_id={test_client.id}&status=ready_for_pickup",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert binders.status_code == 200
    ready_ids = {item["id"] for item in binders.json()["items"]}
    assert first_binder_id in ready_ids
    assert second_binder_id not in ready_ids
