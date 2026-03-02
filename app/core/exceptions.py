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

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorResponse:
    """Standard error response format."""

    @staticmethod
    def build(
        status_code: int,
        detail: Any,
        error_type: str = "error",
    ) -> dict[str, Any]:
        """Build response with legacy `detail` plus structured `error`."""
        return {
            "detail": detail,
            "error": {
                "type": error_type,
                "detail": detail if isinstance(detail, str) else "Invalid request data",
                "status_code": status_code,
            },
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


def setup_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"path": request.url.path},
        )
        return _error_json(exc.status_code, exc.detail, "http_error")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
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

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle database errors."""
        logger.error(
            "Database error occurred",
            exc_info=exc,
            extra={"path": request.url.path},
        )
        return _error_json(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error", "database_error")

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors."""
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            extra={"path": request.url.path},
        )
        return _error_json(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error", "server_error")
