from datetime import date

from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client


def test_secretary_cannot_see_charge_amounts(client, secretary_headers, advisor_headers, test_db):
    """Test secretary cannot see charge amounts."""
    test_client = Client(
        full_name="Auth Test",
        id_number="700000002",
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    test_business = Business(
        client_id=test_client.id,
        opened_at=date.today(),
    )
    test_db.add(test_business)
    test_db.commit()
    test_db.refresh(test_business)

    create_response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={
            "business_id": test_business.id,
            "amount": 500.0,
            "charge_type": "monthly_retainer",
        },
    )
    assert create_response.status_code == 201

    secretary_response = client.get("/api/v1/charges", headers=secretary_headers)
    assert secretary_response.status_code == 200
    secretary_data = secretary_response.json()

    if secretary_data["items"]:
        first_item = secretary_data["items"][0]
        assert "amount" not in first_item

    advisor_response = client.get("/api/v1/charges", headers=advisor_headers)
    assert advisor_response.status_code == 200
    advisor_data = advisor_response.json()

    if advisor_data["items"]:
        first_item = advisor_data["items"][0]
        assert "amount" in first_item
