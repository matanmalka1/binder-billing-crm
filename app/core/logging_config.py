"""
Structured logging for production observability.

Provides consistent log format with:
- Timestamp
- Level
- Message
- Request ID (when available)
- Stack traces for errors
"""
import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Context variable for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields."""
        request_id = request_id_ctx.get()

        # Base fields
        parts = [
            f"timestamp={self.formatTime(record)}",
            f"level={record.levelname}",
        ]

        # Add request ID if available
        if request_id:
            parts.append(f"request_id={request_id}")

        # Add message
        parts.append(f'message="{record.getMessage()}"')

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            parts.append(f'exception="{exc_text}"')

        return " ".join(parts)


def setup_logging(level: str = "INFO") -> None:
    """
    Setup structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def set_request_id(request_id: str) -> None:
    """Set request ID for current context."""
    request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear request ID from current context."""
    request_id_ctx.set(None)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)