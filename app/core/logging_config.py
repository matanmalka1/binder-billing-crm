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
from dataclasses import dataclass, field

# Context variable for request tracking
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
request_log_stats_ctx: ContextVar["RequestLogStats | None"] = ContextVar(
    "request_log_stats",
    default=None,
)


@dataclass
class RequestLogStats:
    """Runtime log counters for one request."""

    request_method: str | None = None
    request_path: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    summary_logged: bool = False
    sql_queries: int = 0
    sql_by_operation: dict[str, int] = field(default_factory=dict)
    sql_transactions: dict[str, int] = field(default_factory=dict)
    sql_total_ms: float = 0
    slowest_sql_ms: float = 0
    app_warnings: int = 0
    app_errors: int = 0

    def record_sql_query(self, statement: str, duration_ms: float) -> None:
        operation = _sql_operation(statement)
        self.sql_queries += 1
        self.sql_by_operation[operation] = self.sql_by_operation.get(operation, 0) + 1
        self.sql_total_ms += duration_ms
        self.slowest_sql_ms = max(self.slowest_sql_ms, duration_ms)

    def record_transaction(self, transaction: str) -> None:
        self.sql_transactions[transaction] = self.sql_transactions.get(transaction, 0) + 1


def _sql_operation(statement: str) -> str:
    stripped = statement.lstrip()
    if not stripped:
        return "OTHER"
    return stripped.split(None, 1)[0].upper()


def begin_request_log_stats() -> None:
    """Start log counters for the current request."""
    request_log_stats_ctx.set(RequestLogStats())


def clear_request_log_stats() -> None:
    """Clear request log counters from current context."""
    request_log_stats_ctx.set(None)


def get_request_log_stats() -> RequestLogStats | None:
    """Return current request log counters, when available."""
    return request_log_stats_ctx.get()


def record_sql_query(statement: str, duration_ms: float) -> None:
    """Record SQL query metrics for the current request."""
    stats = request_log_stats_ctx.get()
    if stats is not None:
        stats.record_sql_query(statement, duration_ms)


def set_request_summary_context(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    """Store request metadata used by the summary log."""
    stats = request_log_stats_ctx.get()
    if stats is None:
        return

    stats.request_method = method
    stats.request_path = path
    stats.status_code = status_code
    stats.duration_ms = duration_ms


def has_request_db_activity() -> bool:
    """Return whether the current request has emitted DB logs."""
    stats = request_log_stats_ctx.get()
    if stats is None:
        return False
    return stats.sql_queries > 0 or bool(stats.sql_transactions)


def format_request_summary(stats: RequestLogStats) -> str:
    """Format the current request summary."""
    request_method = stats.request_method or "UNKNOWN"
    request_path = stats.request_path or "unknown"
    status_code = stats.status_code if stats.status_code is not None else 500
    duration_ms = stats.duration_ms if stats.duration_ms is not None else 0

    lines = [
        "SUMMARY",
        f"  request: {request_method} {request_path} {status_code}",
        f"  duration: {duration_ms:.1f}ms",
        f"  SQL queries: {stats.sql_queries}",
    ]

    for operation, count in sorted(stats.sql_by_operation.items()):
        lines.append(f"  {operation}: {count}")

    for transaction, count in sorted(stats.sql_transactions.items()):
        lines.append(f"  {transaction}: {count}")

    lines.extend(
        [
            f"  SQL total: {stats.sql_total_ms:.1f}ms",
            f"  slowest query: {stats.slowest_sql_ms:.1f}ms",
            f"  app warnings: {stats.app_warnings}",
            f"  errors: {stats.app_errors}",
        ]
    )

    return "\n".join(lines)


def log_request_summary(logger: logging.Logger) -> None:
    """Log the current request summary once."""
    stats = request_log_stats_ctx.get()
    if stats is None or stats.summary_logged:
        return

    stats.summary_logged = True
    logger.info(format_request_summary(stats))


class StructuredFormatter(logging.Formatter):
    """Structured log formatter."""

    def _format_prefix(self, record: logging.LogRecord) -> str:
        request_id = request_id_ctx.get()
        parts = [
            f"[{self.formatTime(record)}]",
            record.levelname,
        ]
        if request_id:
            parts.append(f"request_id={request_id}")
        return " ".join(parts)

    def _indent(self, text: str) -> str:
        return "\n".join(f"  {line}" if line else "" for line in text.splitlines())

    def _format_sqlalchemy(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        prefix = f"{self._format_prefix(record)} SQL"
        stats = request_log_stats_ctx.get()

        if stats is not None:
            if message.startswith("BEGIN"):
                stats.record_transaction("BEGIN")
            elif message == "COMMIT":
                stats.record_transaction("COMMIT")
            elif message == "ROLLBACK":
                stats.record_transaction("ROLLBACK")

        if message.startswith("["):
            return f"{prefix}\n  {message}"

        return f"{prefix}\n{self._indent(message)}"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields."""
        if record.name.startswith("sqlalchemy.engine"):
            return self._format_sqlalchemy(record)

        stats = request_log_stats_ctx.get()
        if stats is not None:
            if record.levelno >= logging.ERROR:
                stats.app_errors += 1
            elif record.levelno >= logging.WARNING:
                stats.app_warnings += 1

        prefix = self._format_prefix(record)
        record_message = record.getMessage()
        if record_message.startswith("SUMMARY\n"):
            message = f"{prefix} SUMMARY\n{record_message.removeprefix('SUMMARY\n')}"
        else:
            message = f"{prefix} {record.name} | {record_message}"

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            message = f"{message}\nexception:\n{self._indent(exc_text)}"

        return message


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
