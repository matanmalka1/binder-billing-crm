# Health Module

> Last audited: 2026-03-17 (domain-by-domain backend sync).


Provides application health/readiness checks for runtime monitoring and deployment verification.

## Scope

This module provides:
- Unauthenticated health endpoint (`/health`)
- Database connectivity verification
- Service + repository layering for readiness checks
- HTTP status mapping (`200` healthy, `503` unhealthy)

## Domain Model

This module does not define persistent database models.

It defines health-check components:
- API endpoint (`health_check`)
- `HealthService`
- `HealthRepository`

Implementation references:
- API: `app/health/api/health.py`
- Service: `app/health/services/health_service.py`
- Repository: `app/health/repositories/health_repository.py`

## API

Router path is `/health` (registered in `app/router_registry.py`, included from `app/main.py`, without `/api/v1` prefix).

### Health check
- `GET /health`
- Auth: none (public/unauthenticated)
- Verifies:
  - Application process is up
  - Database session can execute a simple query

Healthy response (`200 OK`):

```json
{
  "status": "healthy",
  "database": "connected"
}
```

Unhealthy response (`503 Service Unavailable`):

```json
{
  "status": "unhealthy",
  "database": "disconnected"
}
```

## Behavior Notes

- `HealthRepository.can_connect()` performs a lightweight ORM query (`db.query(1).first()`).
- Any query exception is normalized to `False` connectivity.
- `HealthService.check()` returns a stable two-field payload:
  - `status`: `healthy` or `unhealthy`
  - `database`: `connected` or `disconnected`
- API handler returns `503` whenever `status != "healthy"`.

## Error Envelope

- Health endpoint normally returns explicit health payloads instead of domain exceptions.
- On unhealthy state, it still returns JSON payload (with `503`) rather than raising app-domain error codes.
- Global exception handlers from `app/core/exceptions.py` still apply to unexpected failures.

## Cross-Domain Integration

- Uses shared database dependency (`app.database.get_db`).
- Used by deployment/monitoring/regression checks to verify core app availability.

## Tests

Health test suites:
- `tests/health/api/test_health.py`
- `tests/health/repository/test_health_repository.py`
- `tests/health/service/test_health_service.py`

Related regression coverage:
- `tests/regression/test_vat_module_regressions.py` (health endpoint unaffected)
- `tests/regression/test_reports_export_manual.py` (external health ping)

Run only this domain:

```bash
pytest tests/health -q
```
