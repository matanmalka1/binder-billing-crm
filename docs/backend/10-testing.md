## Scope
This file owns only:
- Backend-local test fixtures, layout, and implementation details.
- Concrete pytest patterns subordinate to canonical YM_Docs testing rules.

This file must not contain:
- Project-wide testing rules that override YM_Docs.
- Product/domain behavior.
- Frontend testing rules.

Source of truth: reference

Canonical project-wide rules:
- `../../../docs/docs/workflow/testing.md`
- `../../../docs/docs/workflow/verification.md`

# Testing

## Running Tests

```bash
# Run tests for a specific domain (preferred — only run what you changed)
JWT_SECRET=test-secret ./.venv/bin/python -m pytest -q tests/binders/

# Run the full suite
JWT_SECRET=test-secret ./.venv/bin/python -m pytest -q
```

The `JWT_SECRET` env var is required because `config.py` validates it at import time. Tests set `APP_ENV=test` and `JWT_SECRET=test-secret` at the top of `tests/conftest.py`.

## Test Database

Tests use SQLite in-memory with `StaticPool` and `check_same_thread=False`. `Base.metadata.create_all()` builds the schema fresh for each test function. The schema is dropped in the fixture's `finally` block.

This is the only place where `Base.metadata.create_all()` is used — the application uses Alembic for all schema management.

From `tests/conftest.py`:
```python
@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = TestSessionLocal()
    seed_default_deadline_rules(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

## Standard Fixtures

| Fixture | Scope | Provides |
|---------|-------|---------|
| `test_db` | function | SQLite in-memory session |
| `test_user` | function | `User` with `ADVISOR` role, committed |
| `secretary_user` | function | `User` with `SECRETARY` role, committed |
| `auth_token` | function | JWT access token for `test_user` |
| `secretary_token` | function | JWT access token for `secretary_user` |
| `advisor_headers` | function | `{"Authorization": "Bearer <token>"}` |
| `secretary_headers` | function | same for secretary |
| `client` | function | `TestClient` with DB overridden to `test_db` |
| `create_client_with_business` | function | Factory that creates client + business |
| `vat_client` | function | Client with a business, for VAT tests |

## Test Helpers

`tests/helpers/identity.py` provides `seed_client_identity()` and `seed_business()`. These are the standard way to set up client/business graph in tests — they create the full `LegalEntity` → `ClientRecord` → `Business` chain.

```python
from tests.helpers.identity import seed_client_identity

def test_something(test_db, test_user):
    client = seed_client_identity(
        test_db,
        full_name="Alpha Client",
        id_number="TEST001",
    )
    binder = Binder(
        client_record_id=client.id,
        binder_number="AA-100",
        location_status=BinderLocationStatus.IN_OFFICE,
        capacity_status=BinderCapacityStatus.OPEN,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)
```

## Service Tests (preferred)

Service tests instantiate the service directly with `test_db` and assert on returned values. They hit real SQLite — no mocking. This is the dominant test pattern:

```python
def test_list_binders_enriched_location_filter(test_db, test_user):
    c1, c2, b1, b2 = _seed_binders(test_db, test_user.id)
    service = BinderListService(test_db)

    items, total, _ = service.list_binders_enriched(location_status="ready_for_handover")

    assert total == 1
    assert items[0].id == b2.id
```

## HTTP Integration Tests

HTTP tests use the `client` fixture (`TestClient`). The `client` fixture overrides `get_db` to use `test_db` and patches out `expire_overdue_requests` (the background job) to avoid side effects:

```python
def test_get_binder_returns_404(client, advisor_headers, test_db, test_user):
    response = client.get("/api/v1/binders/999999", headers=advisor_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
```

## What Not to Mock

The DB is not mocked — tests hit SQLite. This ensures repository query correctness and ORM relationship behavior are tested. Do not mock `Session` or repository methods in service tests.

## File Layout

```
tests/
├── conftest.py               # Global fixtures
├── helpers/
│   └── identity.py          # seed_client_identity, seed_business
└── <domain>/
    ├── service/
    │   └── test_<service>.py
    └── api/
        └── test_<router>.py
```

Not every domain has both service and API test files. Service tests are prioritized for logic-heavy services.

## Naming Conventions

Test functions follow `test_<what>_<condition>`. Private setup helpers inside test files are prefixed with `_`:

```python
def _seed_binders(db, user_id: int): ...  # setup helper
def test_list_binders_enriched_status_filter(test_db, test_user): ...
```
