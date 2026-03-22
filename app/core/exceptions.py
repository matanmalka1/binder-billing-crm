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

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ErrorResponse:
    """Standard error response format."""

    @staticmethod
    def build(
        status_code: int,
        detail: Any,
        error_type: str = "error",
    ) -> dict[str, Any]:
        """Build response with legacy and structured error fields."""
        structured = {
            "type": error_type,
            "detail": detail if isinstance(detail, str) else "נתוני הבקשה אינם תקינים",
            "status_code": status_code,
        }
        return {
            "detail": detail,
            "error": error_type,
            "error_meta": structured,
        }


def _error_json(status_code: int, detail: Any, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse.build(
            status_code=status_code,
            detail=detail,
            error_type=error_type,
        ),
    )


# ── Application-level domain errors ─────────────────────────────────────────


class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


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


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"path": request.url.path},
    )
    return _error_json(exc.status_code, exc.detail, "http_error")


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    logger.warning(
        f"Validation error: {errors}",
        extra={"path": request.url.path},
    )
    # Pydantic v2 may include non-serializable Exception objects in ctx.
    # Sanitize each error dict to make it JSON-safe.
    safe_errors = []
    for err in errors:
        safe_err = {k: v for k, v in err.items() if k != "ctx"}
        if "ctx" in err:
            safe_ctx = {
                ck: str(cv) if isinstance(cv, Exception) else cv
                for ck, cv in err["ctx"].items()
            }
            safe_err["ctx"] = safe_ctx
        safe_errors.append(safe_err)
    return _error_json(status.HTTP_422_UNPROCESSABLE_ENTITY, safe_errors, "validation_error")


async def _database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error(
        "Database error occurred",
        exc_info=exc,
        extra={"path": request.url.path},
    )
    return _error_json(status.HTTP_500_INTERNAL_SERVER_ERROR, "שגיאת שרת פנימית", "database_error")


async def _general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={"path": request.url.path},
    )
    return _error_json(status.HTTP_500_INTERNAL_SERVER_ERROR, "שגיאת שרת פנימית", "server_error")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_json(exc.status_code, exc.message, exc.code)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Normalize ValueError responses to standard error envelope."""
    return _error_json(
        status.HTTP_400_BAD_REQUEST,
        str(exc),
        "validation_error",
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers in one place.

    Registering here (rather than splitting across main.py) ensures that no
    handler is accidentally omitted when the app is initialised.
    """
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, _database_exception_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    # Catch-all — must be last so more specific handlers take priority.
    app.add_exception_handler(Exception, _general_exception_handler)