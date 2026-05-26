from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    request_id: str | None = getattr(getattr(request, "state", None), "request_id", None)
    error: dict[str, Any] = {
        "code": "rate_limit_exceeded",
        "message": "יותר מדי ניסיונות. נסה שוב בעוד כמה דקות.",
        "details": None,
    }
    if request_id:
        error["request_id"] = request_id
    return JSONResponse(status_code=429, content={"error": error})


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_email_key(prefix: str) -> Callable[[Request], str]:
    """Build a SlowAPI key function using request email when available."""

    def _key_func(request: Request) -> str:
        ip = get_remote_address(request)
        try:
            body_bytes: bytes = getattr(request, "_body", b"")
            if body_bytes:
                data = json.loads(body_bytes)
                raw_email = data.get("email", "")
                if isinstance(raw_email, str) and raw_email.strip():
                    return f"{prefix}:{normalize_email(raw_email)}"
        except Exception:
            logger.debug("rate_limit: could not parse email from body, falling back to IP")
        return f"{prefix}:ip:{ip}"

    return _key_func


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
