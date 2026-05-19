"""
Request ID middleware for request tracking.

Generates unique request ID for each request and propagates
it through logging context.
"""

import uuid
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import (
    begin_request_log_stats,
    clear_request_id,
    clear_request_log_stats,
    get_logger,
    has_request_db_activity,
    log_request_summary,
    set_request_id,
    set_request_summary_context,
)

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests with unique IDs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Generate request ID and propagate through context."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set in logging context
        set_request_id(request_id)
        begin_request_log_stats()

        started_at = perf_counter()
        status_code = 500
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            set_request_summary_context(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )

            if not has_request_db_activity():
                log_request_summary(logger)
                clear_request_log_stats()
                clear_request_id()
