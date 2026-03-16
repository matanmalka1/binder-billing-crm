# Middleware Module

Provides application middleware components for request lifecycle concerns, currently focused on request correlation/tracing.

## Scope

This module provides:
- Request ID generation/extraction middleware
- Request ID propagation into logging context
- Response header propagation (`X-Request-ID`)
- Per-request context cleanup after response

## Domain Model

This module does not define persistent database models.

It defines middleware components:
- `RequestIDMiddleware`

Implementation references:
- Middleware package: `app/middleware/__init__.py`
- Request ID middleware: `app/middleware/request_id.py`

## API

There is currently no standalone HTTP router under `app/middleware`.

Behavior is applied globally through app middleware registration in `app/main.py`:
- `app.add_middleware(RequestIDMiddleware)`

### Request ID header behavior

For every HTTP request:
- If incoming `X-Request-ID` exists, it is reused.
- Otherwise a UUID is generated.
- The request id is added to logging context.
- Response includes `X-Request-ID` with the same value.
- Logging context is cleared at request end.

## Behavior Notes

- Middleware is implemented with `BaseHTTPMiddleware`.
- Request ID context operations use `set_request_id` / `clear_request_id` from `app.core.logging_config`.
- The middleware is non-domain-specific and applies across all routes.
- `RequestIDMiddleware` is registered before CORS middleware in `app/main.py`.

## Error Envelope

- Middleware itself does not define domain error codes.
- Exceptions continue through global exception handlers configured in `app/main.py` via `app/core/exceptions.py`.

## Cross-Domain Integration

- Integrates with `app/core/logging_config.py` to enrich logs with request correlation id.
- Applies uniformly to all domain routers included in `app/main.py`.

## Tests

There is currently no dedicated `tests/middleware` suite.

Middleware behavior is validated indirectly through API/integration tests where requests traverse the full FastAPI stack.

Run broad API coverage:

```bash
pytest tests -q
```
