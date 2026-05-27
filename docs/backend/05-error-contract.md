# Error Contract

## Response Envelope

Errors handled by the central exception handlers return the same JSON shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "המשאב לא נמצא",
    "details": null,
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

`request_id` is included when available (set by `RequestIDMiddleware`). `details` is `null` for most errors; validation errors populate it with a list of field-level errors. SlowAPI rate-limit errors use the same envelope but return `rate_limit_exceeded` as their code.

## HTTP Status → Error Code Mapping

| HTTP | `code` | Default `message` |
|------|--------|-------------------|
| 400 | `bad_request` | "הבקשה אינה תקינה" |
| 401 | `unauthorized` | "נדרש אימות" |
| 403 | `forbidden` | "אין הרשאה לביצוע הפעולה" |
| 404 | `not_found` | "המשאב לא נמצא" |
| 405 | `method_not_allowed` | "שיטת הבקשה אינה נתמכת" |
| 409 | `conflict` | "הבקשה מתנגשת עם מצב קיים" |
| 422 | `validation_error` | "חלק מהשדות אינם תקינים" |
| 429 | `rate_limited` | "בוצעו יותר מדי בקשות" |
| 500 | `internal_server_error` | "אירעה שגיאה לא צפויה" |

The `code` field is a stable machine-readable string. Clients should match on `code`, not `message`.

## Domain Exception Classes

`app/core/exceptions.py` defines the base hierarchy:

```python
class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400, details=None):
        ...

class NotFoundError(AppError):      # status_code=404
class ConflictError(AppError):      # status_code=409
class ForbiddenError(AppError):     # status_code=403
```

Raise these from services. The `app_error_handler` converts them to the error envelope automatically.

Example:
```python
raise NotFoundError(
    f"קלסר {binder_id} לא נמצא",
    "BINDER.NOT_FOUND",
)
```

The `code` field for domain errors uses the pattern `DOMAIN.REASON` (e.g. `BINDER.NOT_FOUND`, `AUTH.INVALID_REFRESH_TOKEN`).

## Validation Error Details

When FastAPI raises `RequestValidationError` (422), `details` is a list:

```json
{
  "error": {
    "code": "validation_error",
    "message": "חלק מהשדות אינם תקינים",
    "details": [
      { "field": "materials.0.period_year", "message": "...", "type": "missing" }
    ]
  }
}
```

The `field` path strips the `body.` prefix — it refers directly to the request body field.

## ValueError Handling

`ValueError` with a Hebrew message string is caught and returned as 400 `bad_request`. This is a shortcut for simple validation that doesn't warrant a full domain exception. Use `AppError` or its subclasses when you need a specific `code`.

## Stack Trace Policy

Stack traces are never included in HTTP responses. They are logged server-side at `ERROR` level via the exception handlers. `SQLAlchemyError` and unhandled `Exception` always log `exc_info=True`.

## What Not to Do

- Do not raise `HTTPException` from services — that couples services to HTTP concerns. Raise `AppError` subclasses.
- Do not use `HTTPException` for domain errors from routers either; prefer `NotFoundError`, `ConflictError`, etc., which produce consistent codes.
- Exception: `get_current_user` in `deps.py` raises `HTTPException` directly since it is itself a FastAPI dependency at the transport layer boundary.
