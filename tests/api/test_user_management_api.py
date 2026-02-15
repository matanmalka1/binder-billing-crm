from app.models import User, UserRole
from app.services import AuthService


def _make_user(test_db, email: str, role: UserRole = UserRole.SECRETARY) -> User:
    user = User(
        full_name="Managed User",
        email=email,
        password_hash=AuthService.hash_password("password123"),
        role=role,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_advisor_can_create_list_and_get_users(client, advisor_headers):
    create_response = client.post(
        "/api/v1/users",
        headers=advisor_headers,
        json={
            "full_name": "New Secretary",
            "email": "new.secretary@example.com",
            "phone": "050-1234567",
            "role": "secretary",
            "password": "password123",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    list_response = client.get("/api/v1/users", headers=advisor_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 2

    get_response = client.get(f"/api/v1/users/{created_id}", headers=advisor_headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "new.secretary@example.com"


def test_secretary_cannot_access_user_management(client, secretary_headers):
    response = client.get("/api/v1/users", headers=secretary_headers)
    assert response.status_code == 403


def test_advisor_can_update_and_activate_deactivate_user(client, advisor_headers, test_db):
    target = _make_user(test_db, "target@example.com")

    update_response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=advisor_headers,
        json={"full_name": "Renamed User", "role": "advisor"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Renamed User"
    assert update_response.json()["role"] == "advisor"

    deactivate_response = client.post(
        f"/api/v1/users/{target.id}/deactivate",
        headers=advisor_headers,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert deactivate_response.json()["token_version"] == 1

    activate_response = client.post(
        f"/api/v1/users/{target.id}/activate",
        headers=advisor_headers,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True


def test_cannot_update_immutable_fields(client, advisor_headers, test_db):
    target = _make_user(test_db, "immutable@example.com")
    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=advisor_headers,
        json={"email": "new@example.com"},
    )
    assert response.status_code == 400


def test_cannot_deactivate_self(client, advisor_headers, test_user):
    response = client.post(f"/api/v1/users/{test_user.id}/deactivate", headers=advisor_headers)
    assert response.status_code == 400

