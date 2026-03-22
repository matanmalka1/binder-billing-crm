from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client


def test_work_queue_endpoint(client, advisor_headers, test_db, test_user):
    """Test work queue endpoint."""
    test_client = Client(
        full_name="WQ Test",
        id_number="WQ001",
    )
    test_db.add(test_client)
    test_db.commit()

    binder = Binder(
        client_id=test_client.id,
        binder_number="WQ-001",
        period_start=date.today() - timedelta(days=5),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    response = client.get("/api/v1/dashboard/work-queue", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_attention_endpoint(client, advisor_headers):
    """Test attention endpoint."""
    response = client.get("/api/v1/dashboard/attention", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_overview_includes_quick_actions(client, advisor_headers):
    """Dashboard overview response includes quick_actions contract field."""
    response = client.get("/api/v1/dashboard/overview", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "quick_actions" in data
    assert isinstance(data["quick_actions"], list)
