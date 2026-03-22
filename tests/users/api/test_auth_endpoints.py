from app.config import config


def _login(client, email: str, password: str, remember_me: bool = False) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "remember_me": remember_me},
    )
    assert response.status_code == 200
    return {"token": response.json()["token"], "set_cookie": response.headers["set-cookie"]}


def test_login_remember_me_extends_cookie_ttl(client, test_user):
    regular = _login(client, test_user.email, "password123", remember_me=False)["set_cookie"]
    remembered = _login(client, test_user.email, "password123", remember_me=True)["set_cookie"]

    regular_max_age = f"Max-Age={int(config.JWT_TTL_HOURS * 3600)}"
    remembered_max_age = f"Max-Age={int(config.JWT_TTL_HOURS * 2 * 3600)}"

    assert regular_max_age in regular
    assert remembered_max_age in remembered


def test_logout_invalidates_old_token_and_clears_cookie(client, test_user):
    login = _login(client, test_user.email, "password123")
    token = login["token"]

    protected_before = client.get(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert protected_before.status_code == 200

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 204
    assert "access_token=" in logout_response.headers["set-cookie"]

    protected_after = client.get(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert protected_after.status_code == 401
