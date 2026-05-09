def test_overview_includes_quick_actions(client, advisor_headers):
    """Dashboard overview response includes quick_actions contract field."""
    response = client.get("/api/v1/dashboard/overview", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "quick_actions" in data
    assert isinstance(data["quick_actions"], list)
