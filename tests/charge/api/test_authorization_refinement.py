from datetime import date

from app.clients.models import Client, ClientType


def test_secretary_cannot_see_charge_amounts(client, secretary_headers, advisor_headers, test_db):
    """Test secretary cannot see charge amounts."""
    test_client = Client(
        full_name="Auth Test",
        id_number="AUTH001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    
    # Advisor creates charge
    create_response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "client_id": test_client.id,
            "amount": 500.0,
            "charge_type": "retainer",
        },
    )
    assert create_response.status_code == 201
    
    # Secretary lists charges
    secretary_response = client.get("/api/v1/charges", headers=secretary_headers)
    assert secretary_response.status_code == 200
    secretary_data = secretary_response.json()
    
    # Verify amount is not in response
    if secretary_data["items"]:
        first_item = secretary_data["items"][0]
        assert "amount" not in first_item
    
    # Advisor sees full data
    advisor_response = client.get("/api/v1/charges", headers=advisor_headers)
    assert advisor_response.status_code == 200
    advisor_data = advisor_response.json()
    
    if advisor_data["items"]:
        first_item = advisor_data["items"][0]
        assert "amount" in first_item