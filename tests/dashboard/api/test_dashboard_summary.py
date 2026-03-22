def test_summary_endpoint_returns_dashboard_contract(client, advisor_headers):
    response = client.get("/api/v1/dashboard/summary", headers=advisor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "binders_in_office" in data
    assert "binders_ready_for_pickup" in data
    assert "open_reminders" in data
    assert "vat_due_this_month" in data
    assert "attention" in data
    assert "items" in data["attention"]
    assert "total" in data["attention"]
