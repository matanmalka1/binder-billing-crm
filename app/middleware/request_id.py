"""
Request ID middleware for request tracking.

Generates unique request ID for each request and propagates
it through logging context.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import clear_request_id, set_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests with unique IDs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Generate request ID and propagate through context."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set in logging context
        set_request_id(request_id)

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            # Clean up context
            clear_request_id()