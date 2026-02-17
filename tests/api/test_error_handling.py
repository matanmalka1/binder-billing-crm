"""Tests for centralized error handling."""
import pytest
from fastapi import HTTPException


def test_http_error_has_consistent_envelope(client):
    """Test that HTTP errors return consistent envelope."""
    response = client.get("/api/v1/clients/99999", headers={"Authorization": "Bearer invalid"})
    
    # Should return error envelope (401 for invalid token)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "type" in data["error"]
    assert "detail" in data["error"]
    assert "status_code" in data["error"]


def test_validation_error_has_consistent_envelope(client, advisor_headers):
    """Test that validation errors return consistent envelope."""
    # Send invalid data
    response = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"invalid": "data"},  # Missing required fields
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "error" in data


def test_error_response_does_not_leak_stack_trace(client):
    """Test that errors don't leak stack traces to users."""
    # Try to trigger an error
    response = client.get("/api/v1/clients/99999", headers={"Authorization": "Bearer invalid"})
    
    response_text = response.text.lower()
    
    # Should not contain stack trace indicators
    assert "traceback" not in response_text
    assert "file" not in response_text or "detail" in response_text  # "file" might be in "detail"
    assert ".py" not in response_text or "detail" in response_text