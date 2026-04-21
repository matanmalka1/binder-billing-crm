from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus

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
