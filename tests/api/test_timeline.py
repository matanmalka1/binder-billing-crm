from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.clients.models.client import Client, ClientType


def test_client_timeline_endpoint(client, advisor_headers, test_db, test_user):
    """Test client timeline endpoint includes action fields."""
    test_client = Client(
        full_name="Timeline Test",
        id_number="TL001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()
    test_db.refresh(test_client)

    binder = Binder(
        client_id=test_client.id,
        binder_number="TL-BND-1",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=2),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    response = client.get(
        f"/api/v1/clients/{test_client.id}/timeline",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == test_client.id
    assert "events" in data
    assert "total" in data
    assert data["total"] >= 1

    first_event = data["events"][0]
    assert "actions" in first_event
    assert "available_actions" in first_event


def test_timeline_requires_auth(client, test_db):
    """Test timeline requires authentication."""
    test_client = Client(
        full_name="Timeline Test",
        id_number="TL002",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(test_client)
    test_db.commit()

    response = client.get(f"/api/v1/clients/{test_client.id}/timeline")
    assert response.status_code == 401
