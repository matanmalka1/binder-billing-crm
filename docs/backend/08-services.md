# Services

## Role

Services own business logic. They are the single entry point for cross-domain orchestration, status transition rules, derived state computation, and DTO mapping. Routers should call one service method per endpoint unless the existing endpoint pattern has a narrow transport concern.

## Instantiation Pattern

Services are instantiated by routers with the injected DB session:

```python
# Router
def list_binders(db: DBSession, user: CurrentUser):
    service = BinderListService(db)
    items, total, counters = service.list_binders_enriched(...)
    return BinderListResponse(...)
```

Services hold references to repositories:

```python
class BinderListService:
    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_record_repo = ClientRecordRepository(db)
```

No service is a singleton. Each request gets a fresh service instance sharing the request's DB session.

## Derived State

Values like `days_in_office`, `urgency`, `available_actions`, and `signals` are computed in the service layer and set on Pydantic response objects. They are never stored in the database.

```python
response.days_in_office = (
    max(0, (ref_date - binder.period_start).days)
    if binder.period_start is not None
    else None
)
response.available_actions = get_binder_actions(binder)
```

## Response Mapping

Services map repository output (ORM models or projection dataclasses) to Pydantic response schemas. Two patterns:

**From ORM model**:
```python
response = BinderResponse.model_validate(binder)  # uses from_attributes=True
response.days_in_office = ...  # set derived fields after
```

**From projection dataclass** (preferred for lists):
```python
@staticmethod
def _row_to_response(row: BinderListRow, ref_date: date) -> BinderResponse:
    return BinderResponse(
        id=row.id,
        client_name=row.client_name,
        days_in_office=max(0, (ref_date - row.period_start).days) if row.period_start else None,
        available_actions=get_binder_actions_for_state(binder_id=row.id, status=row.status),
    )
```

## Split Service Files

Large domains split service logic across multiple files by responsibility:

```
app/binders/services/
├── binder_service.py        # writes: create, update status, delete
└── binder_list_service.py   # reads: list, enrich, single get
```

`BinderListService` is read-only. `BinderService` handles mutations. Both share the same DB session. This separation keeps files small and makes the read path testable in isolation.

## Cross-Domain Orchestration

Cross-domain writes (e.g. creating a binder triggers a notification) live in the service layer, not routers. The service instantiates repositories from both domains and coordinates the transaction:

```python
class ClientOnboardingOrchestrator:
    def __init__(self, db: Session):
        self.binder_repo = BinderRepository(db)
        self.vat_repo = VatReportRepository(db)
        self.notification_service = NotificationService(db)
        ...
```

`db.flush()` is used between steps within the same transaction. `db.commit()` is called by `get_db()` at request end unless the service needs to commit before external I/O.

## Idempotency

Sensitive write operations (imports, bulk actions, notification sends) accept and check an idempotency key. The `IdempotencyService` from `app/infrastructure/idempotency/` stores request fingerprints and returns cached responses on replay.

`NotificationService.exists_for_binder_trigger()` prevents duplicate notification sends by checking for a prior record before creating a new one.

## Business Rules in Services (not Routers)

All branching logic lives in services. Routers must not contain `if`/`elif`/`else` that dispatch to different code paths based on business state.

Bad (in router):
```python
if binder.status == BinderStatus.IN_OFFICE:
    service.mark_ready(binder_id)
else:
    raise HTTPException(400, "...")
```

Correct (in service):
```python
def mark_ready_for_pickup(self, binder_id: int) -> Binder:
    binder = self.binder_repo.get_by_id(binder_id)
    if not binder:
        raise NotFoundError(...)
    if binder.status != BinderStatus.IN_OFFICE:
        raise ConflictError("קלסר אינו במצב קבלה", "BINDER.INVALID_STATUS_TRANSITION")
    return self.binder_repo.update_status(binder_id, BinderStatus.READY_FOR_PICKUP, ...)
```

## Fine-Grained Authorization

Role checks in `require_role()` handle coarse-grained access (ADVISOR vs SECRETARY). Fine-grained checks (e.g. "secretary cannot delete") are done in the service:

```python
def delete_binder(self, binder_id: int, actor_id: int, actor_role: UserRole) -> bool:
    if actor_role == UserRole.SECRETARY:
        raise ForbiddenError("מזכירה אינה מורשית למחוק קלסר", "BINDER.DELETE_FORBIDDEN")
    ...
```

In practice, many fine-grained restrictions are expressed at the router level with a tighter `require_role()`; service-layer checks are still used where the rule depends on domain state.

## What Services Must Not Do

- No SQL queries — call repositories instead
- No `db.query(...)` — use repositories
- No `raise HTTPException` — raise `AppError` subclasses
- No Alembic or schema-level operations
- No direct `db.execute(raw_sql)` — no raw SQL
