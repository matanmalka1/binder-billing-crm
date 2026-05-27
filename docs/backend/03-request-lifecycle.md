# Request Lifecycle

## Middleware Stack (outermost → innermost)

1. **RequestIDMiddleware** — generates/propagates `X-Request-ID`, starts per-request log stats, records HTTP metadata, writes the request summary log on completion
2. **CORSMiddleware** — sets `Access-Control-Allow-*` headers
3. **FastAPI routing + exception handlers**
4. **SlowAPI route limiter** — the login endpoint is decorated with `AUTH_LOGIN_RATE_LIMIT` (default: 5/minute outside tests)
5. **`get_db()` dependency** — opens session, commits on clean exit, rolls back on exception, logs SQL summary

## Per-Request Tracing

`RequestIDMiddleware` sets a `ContextVar`-backed request ID at the start of each request. All log records in that request inherit the ID from the context. The ID comes from the `X-Request-ID` header if present, otherwise a new UUID4. It is echoed back in the `X-Request-ID` response header.

## DB Session Lifecycle

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()          # commits on clean return
    except Exception:
        db.rollback()        # rolls back on any exception
        raise
    finally:
        db.close()
        log_request_summary(...)   # emits SQL stats summary
        clear_request_log_stats()
        clear_request_id()
```

Services that coordinate external I/O (file uploads, notification sends) call `db.commit()` or `db.rollback()` themselves before the external call. The `get_db()` commit/rollback is a no-op for already-committed sessions.

## Router → Service → Repository Flow

```
HTTP request
  → Middleware (request ID, rate limit, CORS)
  → FastAPI route handler
      → Auth: get_current_user / require_role
      → Inject DBSession
      → Instantiate Service(db)
      → Call service method
          → Instantiate Repository(db)
          → Build select() statement
          → db.scalars(...).all() / db.execute(...)
          → Return ORM models or typed projections
      → Map result to Pydantic response schema
      → Return response
  → get_db() commits / rolls back
  → Middleware writes request summary log
```

## Error Flow

Exceptions propagate up through FastAPI's exception handler registry:

| Exception type | Handler | HTTP status |
|---|---|---|
| `AppError` (and subclasses) | `app_error_handler` | `exc.status_code` |
| `NotFoundError` | (subclass of AppError) | 404 |
| `ConflictError` | (subclass of AppError) | 409 |
| `ForbiddenError` | (subclass of AppError) | 403 |
| `StarletteHTTPException` | `http_exception_handler` | `exc.status_code` |
| `RequestValidationError` | `validation_exception_handler` | 422 |
| `SQLAlchemyError` | `database_exception_handler` | 500 |
| `ValueError` (with Hebrew message) | `value_error_handler` | 400 |
| `Exception` (catch-all) | `general_exception_handler` | 500 |

All handlers call `error_response()` which returns a consistent JSON envelope (see [05-error-contract.md](05-error-contract.md)).

## Startup (lifespan)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    run_development_tax_calendar_bootstrap()  # dev only: pre-seeds tax calendar
    run_startup_expiry()                       # marks overdue items on startup
    expiry_task = asyncio.create_task(daily_expiry_job())
    yield
    expiry_task.cancel()
```

`daily_expiry_job` sleeps for `BACKGROUND_JOB_INTERVAL_SECONDS` (default 86,400 seconds) between runs and currently expires overdue signature requests.

## Static Files (dev/test only)

In `development` and `test`, `./storage/` is mounted at `/local-storage/*` via `StaticFiles`. Production does not expose local storage — files are served from R2.
