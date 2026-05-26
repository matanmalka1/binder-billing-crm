import json
from asyncio import run

from starlette.requests import Request

from app.middleware.rate_limiting import (
    get_email_key,
    normalize_email,
    rate_limit_exceeded_handler,
)


def _request(*, body: bytes = b"", client: tuple[str, int] = ("127.0.0.1", 12345)) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": client,
    }
    request = Request(scope)
    request._body = body
    return request


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_email_key_uses_cached_json_body_email():
    request = _request(body=json.dumps({"email": " User@Example.COM "}).encode())

    assert get_email_key("auth_login")(request) == "auth_login:user@example.com"


def test_email_key_falls_back_to_ip_for_missing_email():
    request = _request(body=json.dumps({"password": "secret"}).encode())

    assert get_email_key("auth_login")(request) == "auth_login:ip:127.0.0.1"


def test_email_key_falls_back_to_ip_for_invalid_json():
    request = _request(body=b"{")

    assert get_email_key("auth_login")(request) == "auth_login:ip:127.0.0.1"


def test_rate_limit_handler_returns_canonical_error_with_request_id():
    request = _request()
    request.state.request_id = "req-1"

    response = run(rate_limit_exceeded_handler(request, Exception()))

    assert response.status_code == 429
    assert json.loads(response.body) == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "יותר מדי ניסיונות. נסה שוב בעוד כמה דקות.",
            "details": None,
            "request_id": "req-1",
        }
    }
