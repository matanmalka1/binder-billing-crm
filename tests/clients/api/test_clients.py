def test_authenticated_client_creation(client, auth_token):
    """Test that authenticated user can create a client."""
    response = client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "full_name": "John Doe",
            "id_number": "123456789",
            "client_type": "osek_murshe",
            "opened_at": "2026-02-08",
            "phone": "0501234567",
            "email": "john@example.com",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["full_name"] == "John Doe"
    assert data["id_number"] == "123456789"
    assert data["status"] == "active"
    assert "available_actions" in data
    assert "id" in data
    actions = data["available_actions"]
    assert any(action["key"] == "freeze" for action in actions)
    freeze_action = next(action for action in actions if action["key"] == "freeze")
    assert freeze_action["id"] == f"client-{data['id']}-freeze"
    assert freeze_action["confirm"] is not None
    assert freeze_action["confirm"]["title"] == "אישור הקפאת לקוח"


def test_client_creation_duplicate_id_number(client, auth_token):
    """Test that duplicate ID numbers are rejected."""
    # Create first client
    client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "full_name": "Jane Doe",
            "id_number": "987654321",
            "client_type": "company",
            "opened_at": "2026-02-08",
        },
    )

    # Attempt duplicate
    response = client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "full_name": "John Smith",
            "id_number": "987654321",
            "client_type": "osek_patur",
            "opened_at": "2026-02-08",
        },
    )

    assert response.status_code == 409


def test_clients_list_includes_available_actions_and_accepts_has_signals(client, auth_token):
    """List response carries action tokens and supports has_signals query flag."""
    create_response = client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "full_name": "Signals Client",
            "id_number": "123123123",
            "client_type": "company",
            "opened_at": "2026-02-08",
        },
    )
    assert create_response.status_code == 201

    list_response = client.get(
        "/api/v1/clients?has_signals=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert list_response.status_code == 200
    data = list_response.json()
    assert "items" in data
    if data["items"]:
        assert "available_actions" in data["items"][0]
