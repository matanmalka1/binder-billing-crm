"""
Centralized exception handling for production safety.

Provides:
- Consistent error envelope
- No stack trace leaks in responses
- Proper error logging with traces
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging_config import get_logger, get_request_id, set_request_error

logger = get_logger(__name__)

REQUEST_LOC_PREFIXES = {"body", "query", "path", "header", "cookie"}

_HTTP_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_server_error",
}

_HTTP_MESSAGE_MAP: dict[int, str] = {
    400: "הבקשה אינה תקינה",
    401: "נדרש אימות",
    403: "אין הרשאה לביצוע הפעולה",
    404: "המשאב לא נמצא",
    405: "שיטת הבקשה אינה נתמכת",
    409: "הבקשה מתנגשת עם מצב קיים",
    422: "חלק מהשדות אינם תקינים",
    429: "בוצעו יותר מדי בקשות",
    500: "אירעה שגיאה לא צפויה",
}


def http_error_code_for_status(status_code: int) -> str:
    if status_code in _HTTP_CODE_MAP:
        return _HTTP_CODE_MAP[status_code]
    if 400 <= status_code < 500:
        return "request_error"
    return "internal_server_error"


def http_error_message_for_status(status_code: int) -> str:
    if status_code in _HTTP_MESSAGE_MAP:
        return _HTTP_MESSAGE_MAP[status_code]
    if 400 <= status_code < 500:
        return "הבקשה אינה תקינה"
    return "אירעה שגיאה לא צפויה"


def contains_hebrew(s: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in s)


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc]
    if parts and parts[0] in REQUEST_LOC_PREFIXES:
        parts = parts[1:]
    return ".".join(parts)


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    if rid is not None:
        return rid
    return get_request_id()


def validation_error_details(errors: list[dict]) -> list[dict]:
    result = []
    for err in errors:
        result.append({
            "field": _field_path(err.get("loc", ())),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        })
    return result


def error_response(
    *,
    code: str,
    message: str,
    details: Any = None,
    request_id: str | None = None,
    status_code: int,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    if request_id is not None:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


# ── Application-level domain errors ─────────────────────────────────────────


class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400, details: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str, code: str):
        super().__init__(message, code, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str, code: str):
        super().__init__(message, code, status_code=409)


class ForbiddenError(AppError):
    def __init__(self, message: str, code: str):
        super().__init__(message, code, status_code=403)


# ── Exception handlers ───────────────────────────────────────────────────────


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"path": request.url.path},
    )
    code = http_error_code_for_status(exc.status_code)
    if isinstance(exc.detail, str) and contains_hebrew(exc.detail):
        message = exc.detail
    else:
        message = http_error_message_for_status(exc.status_code)
    return error_response(
        code=code,
        message=message,
        details=None,
        request_id=_request_id(request),
        status_code=exc.status_code,
    )


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"path": request.url.path},
    )
    details = validation_error_details(exc.errors())
    return error_response(
        code="validation_error",
        message="חלק מהשדות אינם תקינים",
        details=details,
        request_id=_request_id(request),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def _database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    set_request_error(exc, error_type="database_error")
    logger.error(
        "Database error occurred",
        exc_info=exc,
        extra={"path": request.url.path},
    )
    return error_response(
        code="internal_server_error",
        message="אירעה שגיאה לא צפויה",
        details=None,
        request_id=_request_id(request),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def _general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    set_request_error(exc, error_type="internal_server_error")
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={"path": request.url.path},
    )
    return error_response(
        code="internal_server_error",
        message="אירעה שגיאה לא צפויה",
        details=None,
        request_id=_request_id(request),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        set_request_error(exc, error_type=exc.code)
    return error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=_request_id(request),
        status_code=exc.status_code,
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    msg = str(exc)
    message = msg if (msg and contains_hebrew(msg)) else "הבקשה אינה תקינה"
    return error_response(
        code="bad_request",
        message=message,
        details=None,
        request_id=_request_id(request),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers in one place."""
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, _database_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    # Catch-all — must be last so more specific handlers take priority.
    app.add_exception_handler(Exception, _general_exception_handler)
