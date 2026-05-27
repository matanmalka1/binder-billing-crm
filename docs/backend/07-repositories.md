# Repositories

## Role

Repositories are the only layer that touches the database. They return ORM model instances or explicit typed projections (dataclasses). They do not contain business logic, validation, or cross-domain orchestration.

## BaseRepository

`app/common/repositories/base_repository.py` provides a generic CRUD base:

```python
class BaseRepository(Generic[ModelType]):
    model: ClassVar[type[ModelType]]  # set in subclass

    def __init__(self, db: Session): ...

    def get(self, entity_id: int, /, *, include_deleted: bool = False) -> ModelType | None
    def get_by_id(self, entity_id: int, /) -> ModelType | None      # alias for get()
    def get_by_ids(self, entity_ids: set[int] | list[int]) -> dict[int, ModelType]
    def get_by_id_for_update(self, entity_id: int, /) -> ModelType | None  # WITH FOR UPDATE
    def add(self, entity: ModelType) -> ModelType                    # flush after add
    def build_and_add(self, **kwargs) -> ModelType                   # construct + flush
    def update(self, entity_id: int, /, **fields) -> ModelType | None
    def soft_delete(self, entity_id: int, /, deleted_by=None) -> bool
    def hard_delete(self, entity_id: int, /) -> bool
    def delete(self, entity_id, /, deleted_by=None, *, hard=False) -> bool

    apply_pagination = staticmethod(_apply_pagination)  # .offset().limit()
    select_base(*, include_deleted=False)               # starts a select(self.model)
```

`_update_entity()` iterates kwargs and sets attributes, then `db.flush()`. `_update_status()` sets `.status` then calls `_update_entity()`.

Subclasses set `model = Binder` at the class level and override or extend as needed.

## Typed Projections

When a list query needs fields from multiple joined tables, avoid loading full ORM objects for every table. Use an explicit projection instead — a `@dataclass(frozen=True)` that maps the columns fetched by the query:

```python
@dataclass(frozen=True)
class BinderListRow:
    id: int
    client_record_id: int
    office_client_number: int | None
    client_name: str
    client_id_number: str
    binder_number: str
    status: BinderStatus
    ...
```

The repository fetches with `db.execute(proj_stmt).all()` and constructs the dataclass:

```python
rows = [
    BinderListRow(
        id=row.id,
        client_name=row.client_name,
        ...
    )
    for row in db.execute(proj_stmt).all()
]
```

This is used in `BinderRepository.list_active_paginated_projected()`. The service receives `BinderListRow` objects and maps them to `BinderResponse` — it does not touch ORM models for this path.

## Pagination

`BaseRepository.apply_pagination(stmt, page, page_size)` applies `.offset((page-1)*page_size).limit(page_size)`. Every list method that accepts `page` / `page_size` calls this.

Count queries run separately: `select(func.count(Model.id))` with the same filters, without pagination.

## Flush vs Commit

Repositories call `db.flush()` after writes. This sends SQL to the database within the current transaction but does not commit. The transaction is committed by `get_db()` at the end of the request (or by the service if it coordinates external I/O).

Never call `db.commit()` from a repository.

## Cross-Domain Imports

Repositories must not import models from other business domains. If a query needs a join to another domain's table (e.g. `LegalEntity` in `BinderRepository`), import that model directly — but only for join clauses, not for loading unrelated entities as business objects.

Cross-domain data fetching that requires loading full entities from another domain belongs in the service layer.

## Scoping Queries to Active Clients

Binders and other client-scoped entities use `scope_to_active_clients_stmt()` from `app/clients/repositories/active_client_scope.py`. This joins `ClientRecord` and filters to non-CLOSED, non-FROZEN clients. Every repository method that lists data visible in the UI applies this scope.

## Naming Conventions

| Method name pattern | Meaning |
|---------------------|---------|
| `get_by_id` | Single entity by PK, returns `None` if missing |
| `list_by_*` | Return all matching rows (may be large) |
| `list_*_paginated` | Return `(list, count)` tuple |
| `count_*` | Return an integer count |
| `map_*_by_*` | Return `dict[key, entity]` for batch lookups |
| `soft_delete` | Set `deleted_at`, not hard delete |

## What Repositories Must Not Do

- No business logic (no status transition rules, no side effects beyond DB writes)
- No cross-domain service calls
- No `db.commit()`
- No Pydantic model construction — return ORM models or projection dataclasses only
- No `raise HTTPException` — repositories are not HTTP-aware
