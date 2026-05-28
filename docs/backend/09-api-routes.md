## Scope
This file owns only:
- Backend-local implementation details for this documentation area.
- Concrete codebase structure, examples, and conventions subordinate to the canonical YM_Docs rules.

This file must not contain:
- Project-wide architecture rules that override YM_Docs.
- Product/domain behavior.
- Frontend rules.

Source of truth: reference

Canonical project-wide rules:
- `../../../docs/docs/architecture/api-contracts.md`
- `../../../docs/docs/architecture/backend.md`

# API Routes

The target public API contract is defined in [`docs/api-contract-standard.md`](../api-contract-standard.md).
This file describes current backend routing patterns and known conventions; when adding or changing list endpoints, prefer the standard contract unless there is a documented reason not to.

## URL Structure

| Type | Pattern | Example |
|------|---------|---------|
| Authenticated API | `/api/v1/*` | `/api/v1/binders` |
| Auth endpoints | `/api/v1/auth/*` | `/api/v1/auth/login` |
| Public | `/`, `/health`, `/ready`, `/info` | `GET /health` |
| Public sign routes | `/sign/{token}/*` | `GET /sign/{token}` |

Most `/api/v1/*` routes require a valid JWT in `Authorization: Bearer <token>`. Auth login, refresh, logout, and password-reset endpoints are mounted under `/api/v1/auth/*` and use their own cookie/body-token flows.

## Router Construction

Each domain has `api/routers.py` that assembles sub-routers:

```python
# app/binders/api/routers.py
from fastapi import APIRouter
from app.binders.api import binders_list_get, binders_receive_return, binders_operations

router = APIRouter()
router.include_router(binders_list_get.router)
router.include_router(binders_receive_return.router)
router.include_router(binders_operations.router)
```

Sub-routers declare their own prefix and auth dependencies:

```python
# app/binders/api/binders_list_get.py
router = APIRouter(
    prefix="/binders",
    tags=["binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
```

## Thin Router Rule

Canonical layering rules: see `../../../docs/docs/architecture/backend.md`. The notes below are backend-local implementation detail.

Routers must not contain business logic. A router endpoint usually does:

1. Parse and validate request parameters (FastAPI does this automatically via Pydantic)
2. Inject `db: DBSession` and `user: CurrentUser`
3. Instantiate and call one service method
4. Wrap the result in a response schema, or raise a transport-level not-found/error for a missing service result where that pattern already exists
5. Return

```python
@router.get("", response_model=BinderListResponse)
def list_binders(
    db: DBSession,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("desc"),
):
    service = BinderListService(db)
    items, total, counters = service.list_binders_enriched(
        status=status_filter,
        sort_by=sort_by or "period_start",
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return BinderListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        counters=counters,
    )
```

## Pagination Convention

Standard paginated list endpoints accept `page: int = Query(1, ge=1)` and `page_size: int = Query(20, ge=1, le=100)`. Response schemas include `items`, `page`, `page_size`, `total`. Some domains extend this with `counters` (e.g. counts by status). New public list contracts should not introduce alternative pagination names.

## Sorting Convention

List endpoints that support sorting should accept `sort_by` and `order`. Services validate sort columns against an allowlist where dynamic sorting is supported. Some existing endpoints still use `sort_dir` or `sort_order`; migrate these by updating their callers to `order` and removing the old names rather than preserving them (see `../../../docs/docs/adr/0001-no-legacy-compatibility.md`).

## Filtering Convention

Filters are passed as query parameters. Most filters are scalar values interpreted by the service/repository; endpoints that need exclusion lists, such as `work_queue.exclude_source_types`, use repeated query parameters.

## Response Models

Every response-bearing endpoint declares `response_model=`. Pydantic validates and serializes the return value. Endpoints that return no body use `status_code=status.HTTP_204_NO_CONTENT`; many return `Response(status_code=204)`, while some handlers simply return `None`.

## 204 No Content Pattern

```python
@router.delete(
    "/{binder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADVISOR))],
)
def delete_binder(binder_id: int, db: DBSession, user: CurrentUser):
    service = BinderService(db)
    deleted = service.delete_binder(binder_id, actor_id=user.id)
    if not deleted:
        raise NotFoundError(BINDER_NOT_FOUND.format(binder_id=binder_id), "BINDER.NOT_FOUND")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

## Current User in Handlers

`user: CurrentUser` injects the `AuthSubject` into the handler. Use `user.id` for audit fields (`created_by`, `deleted_by`), and `user.role` for fine-grained checks when needed.

## Tags

Each router sets `tags=["<domain>"]`. Tags control grouping in `/docs` (Swagger UI).

## Mounted Routers Summary

From `app/router_registry.py`:

| Router | Prefix |
|--------|--------|
| `health_router` | (no prefix — routes at `/health`) |
| All others | `/api/v1` |
| `signer_router` | (no prefix — routes at `/sign/{token}/*`) |

The `signer_router` is a public router for the signature flow — no auth required.
