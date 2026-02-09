"""Tests for JWT expiration enforcement."""
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt

from app.config import config
from app.models import User, UserRole
from app.services import AuthService


def test_jwt_has_expiration(test_user):
    """Test that generated JWT tokens have explicit expiration."""
    token = AuthService.generate_token(test_user)
    
    # Decode without verification to inspect payload
    payload = jwt.decode(token, options={"verify_signature": False})
    
    assert "exp" in payload
    assert "iat" in payload
    assert isinstance(payload["exp"], int)
    assert isinstance(payload["iat"], int)


def test_jwt_expiration_is_enforced():
    """Test that expired tokens are rejected."""
    # Create a token that's already expired
    past_time = datetime.utcnow() - timedelta(hours=10)
    
    payload = {
        "sub": "123",
        "email": "test@example.com",
        "role": "advisor",
        "iat": past_time,
        "exp": past_time + timedelta(hours=1),  # Expired 9 hours ago
    }
    
    expired_token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    
    # Should reject expired token
    result = AuthService.decode_token(expired_token)
    assert result is None


def test_valid_token_is_accepted(test_user):
    """Test that valid non-expired tokens are accepted."""
    token = AuthService.generate_token(test_user)
    
    # Should accept valid token
    result = AuthService.decode_token(token)
    
    assert result is not None
    assert result["sub"] == str(test_user.id)
    assert result["email"] == test_user.email


def test_token_without_required_fields_rejected():
    """Test that tokens without required fields are rejected."""
    payload = {
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        # Missing "sub" and "role"
    }
    
    token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    
    result = AuthService.decode_token(token)
    assert result is None


def test_expired_token_rejected_in_api(client, test_user):
    """Test that expired token is rejected by API."""
    # Create expired token
    past_time = datetime.utcnow() - timedelta(hours=10)
    
    payload = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role.value,
        "iat": past_time,
        "exp": past_time + timedelta(hours=1),
    }
    
    expired_token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
    
    # Try to use expired token
    response = client.get(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == 401