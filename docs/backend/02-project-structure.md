# Project Structure

## Top-Level Layout

```
app/
├── main.py                  # FastAPI app construction, public routes, middleware wiring
├── config.py                # pydantic-settings Settings class; single settings singleton
├── database.py              # SQLAlchemy engine, SessionLocal, Base, get_db dependency
├── lifespan.py              # Startup/shutdown: tax calendar bootstrap, daily expiry job
├── router_registry.py       # register_routers() — mounts all domain routers
├── model_registry.py        # Imports every model module so SQLAlchemy mappers configure
│
├── <domain>/                # One directory per bounded domain (see below)
│
├── common/                  # Shared enums, BaseRepository, soft-delete, period utils
├── core/                    # Exceptions, exception handlers, logging, env validator, API types
├── infrastructure/          # Storage provider, notification channels, idempotency
├── middleware/              # RequestIDMiddleware, rate limiting
├── actions/                 # UI action registry and action builders
├── utils/                   # General helpers (time, enums, Excel, ID validation)
├── seed/                    # Development data seeding orchestrator and builders
└── tasks/                   # Manual user-task domain linked to work queue items
```

## Domain Directory Layout

```
app/<domain>/
├── api/
│   ├── routers.py           # Assembles sub-routers into a single router for register_routers()
│   └── <feature>.py         # One file per feature group (e.g. binders_list_get.py)
├── services/
│   └── <feature>_service.py
├── repositories/
│   └── <entity>_repository.py
├── schemas/
│   └── <entity>.py          # Request and response models in the same file
└── models/
    └── <entity>.py          # ORM model declarations
```

Some read-only or aggregator domains intentionally omit layers they do not need. For example, `dashboard`, `reports`, `search`, `timeline`, and `work_queue` have no ORM models of their own.

Binders is a good reference domain with several sub-routers:

```
app/binders/api/
├── routers.py
├── binders_list_get.py      # GET /binders, GET /binders/{id}, DELETE /binders/{id}
├── binders_receive_return.py
├── binders_operations.py
├── binders_history.py
├── binders_reminders.py
└── client_binders_router.py
```

## Key Files

| File                                         | Role                                                                                                               |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `app/main.py`                                | FastAPI construction; mounts CORS, rate limit, RequestID middleware; registers routers; serves `./storage/` in dev |
| `app/config.py`                              | `Settings` via pydantic-settings. Single `settings` singleton imported everywhere                                  |
| `app/database.py`                            | Engine with `pool_pre_ping`, SQL query timing hooks, `get_db()` dependency                                         |
| `app/users/api/deps.py`                      | `get_current_user`, `require_role()`, `CurrentUser`, `DBSession` type aliases                                      |
| `app/core/exceptions.py`                     | `AppError`, `NotFoundError`, `ConflictError`, `ForbiddenError`; `error_response()` builder                         |
| `app/core/exception_handlers.py`             | FastAPI handlers for all exception types                                                                           |
| `app/core/logging_config.py`                 | `StructuredFormatter`, per-request stats, `log_request_summary()`                                                  |
| `app/core/api_types.py`                      | `ApiDateTime`, `ApiDecimal`, `PaginatedResponse`                                                                   |
| `app/common/repositories/base_repository.py` | `BaseRepository[T]` with CRUD helpers, soft-delete, pagination                                                     |

## Router Registration

`app/router_registry.py` calls `register_routers(app)` which mounts every domain router. Authenticated API routers use prefix `/api/v1`. Public routes (`/`, `/info`, `/health`, `/ready`, `/sign/{token}`) use no prefix.

## Model Registry

`app/model_registry.py` is imported in `router_registry.py` to guarantee all ORM models are loaded before SQLAlchemy's mapper configuration runs. Alembic imports this same module for autogenerate.
