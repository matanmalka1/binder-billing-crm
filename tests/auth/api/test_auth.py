import jwt
from app.config import config


def test_login_returns_valid_jwt(client, test_user):
    """Test that login returns a valid JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "token" in data
    assert "user" in data
    assert data["user"]["id"] == test_user.id
    assert data["user"]["full_name"] == "Test User"
    assert data["user"]["role"] == "advisor"
    
    # Validate JWT structure
    token = data["token"]
    payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    
    assert "sub" in payload
    assert "email" in payload
    assert "role" in payload
    assert "tv" in payload
    assert "iat" in payload
    assert "exp" in payload
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "advisor"
    assert payload["tv"] == 0


def test_login_invalid_credentials(client, test_user):
    """Test that invalid credentials return 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
