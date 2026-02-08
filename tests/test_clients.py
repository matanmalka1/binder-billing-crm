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
            "email": "john@example.com"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["full_name"] == "John Doe"
    assert data["id_number"] == "123456789"
    assert data["status"] == "active"
    assert "id" in data


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
            "opened_at": "2026-02-08"
        }
    )
    
    # Attempt duplicate
    response = client.post(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "full_name": "John Smith",
            "id_number": "987654321",
            "client_type": "osek_patur",
            "opened_at": "2026-02-08"
        }
    )
    
    assert response.status_code == 409