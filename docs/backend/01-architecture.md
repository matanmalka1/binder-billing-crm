# Architecture

## Overview

Binder & Billing CRM is a FastAPI backend for an internal staff CRM covering clients, binders, billing, tax, VAT reports, and notifications. The UI is Hebrew-only. Two roles: `ADVISOR` (full access), `SECRETARY` (operational, limited write).

## Stack

| Component | Choice |
|-----------|--------|
| Runtime | Python 3.12+ |
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (`select()` style) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT HS256 + bcrypt, `token_version` invalidation |
| DB | PostgreSQL (dev and prod) |
| Storage | Local filesystem in dev/test; Cloudflare R2 in staging/prod |
| Deployment | Render (`render.yaml`) |

## Layer Model

Every routed domain follows exactly this vertical slice:

```
app/<domain>/
├── api/           # Routers — parse request, call service, return response
├── services/      # Business logic, orchestration, DTO mapping
├── repositories/  # ORM queries only — return ORM models or typed projections
├── schemas/       # Pydantic v2 request/response models
└── models/        # SQLAlchemy ORM declarations
```

Data flows in one direction: `Router → Service → Repository → ORM → DB`.

Cross-domain writes are orchestrated in services. Cross-domain read joins are allowed in repositories when they are only used for scoping or typed read projections; loading and coordinating another domain's business entity belongs in services. Read-model domains such as `dashboard`, `reports`, `search`, `timeline`, and `work_queue` aggregate across domains by design.

## Domain Classification

**Routed domains** (have `api/` router, mounted at `/api/v1/*`):

`advance_payments`, `annual_reports`, `audit`, `authority_contact`, `binders`, `businesses`, `charge`, `clients`, `correspondence`, `dashboard`, `health`, `notes`, `notification`, `permanent_documents`, `reminders`, `reports`, `search`, `signature_requests`, `tasks`, `tax_calendar`, `timeline`, `users`, `vat_reports`, `work_queue`

**Internal-only domains** (full layer stack, no HTTP router — consumed by other services):

`invoice`

**Cross-cutting packages** (no layer structure):

| Package | Purpose |
|---------|---------|
| `app/common/` | Shared enums, `BaseRepository`, soft-delete helpers |
| `app/core/` | Exceptions, logging, env validation, API types |
| `app/infrastructure/` | Storage provider, notification channels, idempotency |
| `app/middleware/` | RequestIDMiddleware, rate limiting |
| `app/actions/` | UI action metadata registry |

## Key Invariants

- No raw SQL in application query code — ORM/select constructs only. Exceptions: Alembic migrations, Alembic environment setup, and seed reset/schema checks.
- No `Base.metadata.create_all()` outside isolated test databases.
- No business logic in routers — all if/elif/else belongs in the service layer.
- Repositories do not import models from other business domains by default.
- All background jobs must be idempotent.
- All user-facing strings in Hebrew (error messages that surface to the UI).
- Sensitive write operations require an idempotency key.

## Derived State

`days_in_office`, `urgency`, `signals`, and action lists are computed in the service layer and never persisted. This drives some in-memory filtering in `work_queue` and `dashboard` where filtering depends on cross-entity computed state.

## Environment

| `APP_ENV` | DB | Storage | Log format |
|-----------|-----|---------|-----------|
| `development` | PostgreSQL local | Local filesystem (`./storage/`) | text |
| `test` | SQLite (default) | Local filesystem | text |
| `staging` / `production` | PostgreSQL remote | Cloudflare R2 | JSON |

Run: `APP_ENV=development ENV_FILE=.env.development ./.venv/bin/python -m app.main`
