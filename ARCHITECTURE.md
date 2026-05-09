# Backend Architecture Standard

This document defines the domain pattern for all new backend work and for
incremental refactors of existing domains.

## Layer Contract

Flow is strict:

```text
API router -> Service -> Repository -> SQLAlchemy ORM
```

Return shapes are also strict:

```text
Repository -> SQLAlchemy model or typed read projection
Service -> Pydantic schema / DTO
API router -> Pydantic schema only
```

Routers parse request inputs, enforce endpoint-level roles, call one service
method, and return the service result. Routers do not branch business workflows.

Services own orchestration, validation, authorization beyond coarse endpoint
roles, transaction boundaries, and response transformation.

Repositories own data access only. They do not commit, rollback, emit user-facing
messages, call other domains, or return API schemas.

## BaseRepository

All write-model repositories should inherit from:

```python
from app.common.repositories.base_repository import BaseRepository


class SomeRepository(BaseRepository[SomeModel]):
    model = SomeModel
```

`BaseRepository` provides SQLAlchemy 2.0 CRUD primitives:

- `get(entity_id, include_deleted=False)`
- `get_by_id(entity_id)`
- `get_by_id_for_update(entity_id)`
- `get_multi(page=1, page_size=20, sort_by=None, sort_order="asc", sortable_fields=None)`
- `paginate(...) -> Page[Model]`
- `count(include_deleted=False)`
- `create(**fields)`
- `add(entity)`
- `update(entity_id, **fields)`
- `update_entity(entity, **fields)`
- `delete(entity_id, deleted_by=None, hard=False)`
- `soft_delete(entity_id, deleted_by=None)`
- `hard_delete(entity_id)`

The base implementation uses `select()`, `scalars()`, and `execute()` style. New
code must not introduce `session.query()`.

Soft delete is automatic for models with `deleted_at`. If `deleted_by` exists it
is populated. Models without `deleted_at` fall back to hard delete.

Repositories may expose domain-specific methods, but those methods must still
return ORM models, scalar values, or typed read projections. Business decisions
belong in services.

## BaseService

Domain services should inherit from:

```python
from app.common.services.base_service import BaseService


class SomeService(BaseService):
    ...
```

Services are the only layer that should call:

- `commit()`
- `rollback()`
- `transaction()`
- external side effects after persistence validation
- cross-repository orchestration

Recommended write pattern:

```python
def create_item(self, payload: ItemCreate, actor_id: int) -> ItemResponse:
    with self.transaction():
        self._validate_create(payload)
        item = self.item_repo.create(**payload.model_dump(), created_by=actor_id)
    return ItemResponse.model_validate(item)
```

Repositories flush so generated IDs are available inside a service transaction.
They do not commit.

## Read-Side Pattern

Use three repository categories:

- `Repository`: write-model repository for one aggregate root.
- `ReadRepository`: optimized read methods that still return ORM models or typed
  projection dataclasses.
- `QueryBuilder`: reusable select builders for complex joins used by multiple
  read repositories.

For complex views such as `ClientRecord + LegalEntity + Person`, prefer a shared
query builder plus a typed projection dataclass:

```text
app/clients/repositories/client_record_query.py
app/clients/repositories/client_record_read_repository.py
```

Use a database view only when the shape is stable, heavily reused outside one
domain, and worth migrating through Alembic. Do not use a DB view for business
logic or derived UX state such as `signals` or `urgency`.

Use a specialized read repository when the query is domain-specific or needs
runtime filters, permissions, pagination, or computed columns.

## Migration Rules

When touching a repository:

1. Replace `db.query()` with `select()` / `scalars()` / `execute()`.
2. Move workflow branching and validations to the service layer.
3. Make repository methods return ORM models, scalar values, or typed projections.
4. Convert dict projections to dataclasses unless the dict is only an internal
   adapter immediately converted by the service.
5. Use `BaseRepository` CRUD instead of reimplementing common get/create/update/delete.
6. Keep API schemas out of repositories.

When touching a service:

1. Own the transaction.
2. Convert models/projections to Pydantic response schemas.
3. Keep all user-facing errors in Hebrew.
4. Keep cross-domain orchestration in services, not repositories.

## Target Domain Layout

```text
app/<domain>/
├── api/
├── services/
├── repositories/
│   ├── <aggregate>_repository.py
│   ├── <aggregate>_read_repository.py
│   └── <aggregate>_query.py
├── schemas/
└── models/
```

