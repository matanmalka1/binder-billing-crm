def test_search_endpoint(client, advisor_headers):
    """Test search endpoint."""
    response = client.get("/api/v1/search", headers=advisor_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data


def test_search_with_query(client, advisor_headers):
    """Test search with query parameter."""
    response = client.get(
        "/api/v1/search?query=test",
        headers=advisor_headers,
    )
    
    assert response.status_code == 200


def test_search_with_sla_and_signal_filters(client, advisor_headers):
    """Test search accepts sprint-6 filters at API boundary."""
    response = client.get(
        "/api/v1/search?sla_state=overdue&signal_type=overdue&signal_type=idle_binder",
        headers=advisor_headers,
    )
    assert response.status_code == 200


def test_search_requires_auth(client):
    """Test search requires authentication."""
    response = client.get("/api/v1/search")
    assert response.status_code == 401
