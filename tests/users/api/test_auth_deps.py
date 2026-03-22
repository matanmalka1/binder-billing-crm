from datetime import UTC, datetime, timedelta

import jwt

from app.config import config
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def test_users_endpoint_requires_token(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json()["detail"] == "חסר טוקן אימות"


def test_users_endpoint_rejects_invalid_and_malformed_tokens(client):
    invalid_response = client.get(
        "/api/v1/users",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert invalid_response.status_code == 401
    assert invalid_response.json()["detail"] == "הטוקן אינו תקין או שפג תוקפו"

    now = datetime.now(UTC)
    malformed_token = jwt.encode(
        {
            "sub": "not-an-int",
            "email": "malformed@example.com",
            "role": "advisor",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "tv": "x",
        },
        config.JWT_SECRET,
        algorithm="HS256",
    )
    malformed_response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {malformed_token}"},
    )
    assert malformed_response.status_code == 401
    assert malformed_response.json()["detail"] == "פורמט הטוקן אינו תקין"


def test_inactive_user_token_is_rejected(client, test_db):
    user = User(
        full_name="Inactive Auth User",
        email="inactive.token@example.com",
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.ADVISOR,
        is_active=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    token = AuthService.generate_token(user)
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "המשתמש לא נמצא או שאינו פעיל"


def test_cookie_fallback_authenticates_without_authorization_header(client, auth_token):
    client.cookies.set("access_token", auth_token)
    response = client.get("/api/v1/users")
    assert response.status_code == 200
