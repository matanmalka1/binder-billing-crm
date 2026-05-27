# Logging and Observability

## Log Format

Two formats controlled by `LOG_FORMAT` in `Settings`:

| Environment | Format | Output |
|-------------|--------|--------|
| `development`, `test` | `text` | Human-readable prefixed lines |
| `staging`, `production` | `json` | Newline-delimited JSON |

Both go to `stdout` via a single `StreamHandler`. `LOG_FORMAT=json` is enforced in staging/production by `config.py` validation.

## Logger Setup

```python
from app.core.logging_config import get_logger
logger = get_logger(__name__)
```

`get_logger` is a thin wrapper around `logging.getLogger`. Every module that logs imports `get_logger(__name__)` at module level.

`setup_logging(level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)` runs once at `app/main.py` startup. It attaches `StructuredFormatter` to the root logger and silences `uvicorn.access` (access logs are redundant — the request summary already covers them).

## Per-Request Stats

`RequestIDMiddleware` starts a `RequestLogStats` dataclass in a `ContextVar` at the start of every non-diagnostic request:

```python
begin_request_log_stats()  # creates RequestLogStats in context
```

The stats object accumulates:
- HTTP method, path, route name, status code, duration_ms
- SQL query count, total SQL time, slowest query, breakdown by operation (SELECT/INSERT/UPDATE)
- Transaction markers (BEGIN/COMMIT/ROLLBACK)
- Actor context (user_id, role)
- Idempotency metadata
- Error type and message
- Application warning/error counts

## SQL Query Tracking

`database.py` registers two SQLAlchemy engine events:

```python
@event.listens_for(engine, "before_cursor_execute")
def _record_query_start(conn, cursor, statement, ...):
    context._query_start_time = perf_counter()

@event.listens_for(engine, "after_cursor_execute")
def _record_query_end(conn, cursor, statement, ...):
    record_sql_query(statement, elapsed_ms)  # feeds RequestLogStats
```

Every SQL statement is timed and categorized by operation. This feeds the N+1 detection heuristic.

## Request Summary Log

Emitted once per request — either in `get_db()` (when there was DB activity) or in `RequestIDMiddleware` (for requests with no DB activity). Never double-logged.

The summary log contains HTTP metadata, SQL stats, actor info, and flags:

```
SUMMARY
  request: GET /api/v1/binders 200
  route: binders.list_binders
  actor: user=1 role=ADVISOR
  duration: 45.2ms
  SQL queries: 3
  SELECT: 3
  SQL total: 12.1ms
  slowest query: 8.3ms
  app warnings: 0
  errors: 0
```

In JSON mode (`log_format=json`), the same data is emitted as a structured `http_request_completed` event with nested `http`, `db`, `actor`, `flags`, and `error` fields.

## Flags and Thresholds

Configurable via `Settings`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `LOG_SLOW_REQUEST_MS` | 500 | Requests slower than this get `slow_request: true` flag |
| `LOG_SLOW_QUERY_MS` | 250 | Slowest query above this gets `slow_query: true` flag |
| `LOG_HIGH_QUERY_COUNT` | 20 | Requests with ≥20 queries get `high_query_count: true` flag |

When any flag fires, the summary log level escalates to `WARNING`. In JSON logs, diagnostic metadata such as client IP, user agent, response length, and per-operation SQL breakdown is included in the structured log event.

`possible_n_plus_one` is flagged when both `high_query_count` is true and SELECT count ≥ `high_query_count`.

## Request ID

Every request gets a UUID4 request ID from `RequestIDMiddleware`. Source priority:
1. `X-Request-ID` header from the client
2. Generated UUID4

The ID is stored in a `ContextVar` (`request_id_ctx`) and included in all log records for that request via `StructuredFormatter`. It is echoed back in the `X-Request-ID` response header.

## Actor Context

After JWT validation in `get_current_user`, `set_actor_context(user_id=..., role=...)` writes actor metadata into `RequestLogStats`. This appears in the request summary log as `actor: user=1 role=ADVISOR`.

## Error Logging

- `AppError` with `status_code < 500`: not logged (client error, not actionable server-side)
- `AppError` with `status_code >= 500`: logged as error via `set_request_error()`
- `SQLAlchemyError`: logged at ERROR with `exc_info=True`
- `Exception` (catch-all): logged at ERROR with `exc_info=True`
- `HTTPException`, `RequestValidationError`: logged at WARNING
- `ValueError`: returned as 400 by the handler; the handler itself does not log it

## Sentry

`app/core/sentry.py` calls `sentry_sdk.init()` when `SENTRY_ENABLED=true`. Configured with `traces_sample_rate` from settings. Not used in development by default (`SENTRY_ENABLED=false`).

## SQL Logging in Development

`LOG_SQL=true` (auto-set in development by `config.py`) enables the `sqlalchemy.engine` logger at `INFO` level. SQL statements are formatted by `StructuredFormatter._format_sqlalchemy()` which adds a `SQL` prefix and request ID.

## Paths Excluded from Logging

`RequestIDMiddleware` skips summary logging for:
```python
_SKIP_LOG_PATHS = {"/", "/health", "/ready", "/docs", "/openapi.json", "/favicon.ico"}
```
These paths get no per-request log stats object and no summary log.
