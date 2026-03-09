"""Tests for health endpoint."""


def test_health_endpoint_returns_200(client):
    """Test that health endpoint returns 200 when healthy."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_health_endpoint_is_unauthenticated(client):
    """Test that health endpoint does not require authentication."""
    response = client.get("/health")
    
    # Should succeed without auth token
    assert response.status_code == 200


def test_health_endpoint_verifies_database(client):
    """Test that health endpoint verifies database connectivity."""
    response = client.get("/health")
    
    # If we get 200, database check passed
    assert response.status_code == 200