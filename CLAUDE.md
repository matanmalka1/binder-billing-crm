# CLAUDE.md 
# Binder & Billing CRM (Backend)

> Single source of truth for assistant behavior and project rules.
---

## Assistant Behavior

- No greetings, affirmations, or filler ("Sure!", "Great question", "I hope this helps")
- Never repeat the user's prompt back to them
- Skip explanations unless explicitly requested
- Think step-by-step internally; output final result only unless reasoning is requested
- Prefer code and bullet points over prose
- Get it right the first time — verify against existing patterns before generating
- **Do not read files not explicitly mentioned in the task — ask if uncertain**

---

## Project Overview

Internal staff CRM: clients, binders, billing, tax, annual reports, VAT, notifications.
UI: Hebrew-only. Roles: `ADVISOR` (full access), `SECRETARY` (operational, read-oriented).
Status: Production-ready through Sprint 9. Sprints 1–9 are **frozen**.

Frontend repo: `../frontend/` — React 19 + TypeScript + Vite + TailwindCSS v4.

---

## Run

```bash
APP_ENV=development ENV_FILE=.env.development python -m app.main
# Docs: http://localhost:8000/docs
```

### Tests

```bash
# Run only relevant tests for the files you changed (default):
JWT_SECRET=test-secret pytest -q tests/<domain_or_path>/...

# Full suite — only when explicitly needed:
# JWT_SECRET=test-secret pytest -q
```

---

## Stack

- FastAPI, SQLAlchemy ORM (no raw SQL), Pydantic v2
- Dev: SQLite; Prod: PostgreSQL
- Migrations: Alembic (`alembic/`) — `Base.metadata.create_all()` is **never** used
- Auth: JWT HS256, `token_version` invalidation on User model

---

## Domain Structure (20 domains + 5 infra)

**Routed domains** (have `api/` router):
`advance_payments`, `annual_reports`, `authority_contact`, `binders`, `charge`, `clients`,
`correspondence`, `dashboard`, `health`, `permanent_documents`, `reminders`, `reports`,
`search`, `signature_requests`, `tax_deadline`, `timeline`, `users`, `vat_reports`

**Internal-only domains** (no HTTP router — used as services by other domains):
`invoice`, `notification` — full layer stack.

**Shared utility:** `common/` — repositories only, no layers.

Every routed domain follows exactly:

```
app/<domain>/
├── api/           # Routers — request/response only
├── services/      # All business logic; cross-domain entry point
├── repositories/  # ORM queries only
├── schemas/       # Pydantic v2 (no ORM coupling)
└── models/        # SQLAlchemy ORM declarations
```

**Infra** (`core/`, `utils/`, `infrastructure/`, `middleware/`, `actions/`) — no layer structure.

---

## Migrations (Alembic)

- All schema changes go through Alembic — never modify the DB directly or use `create_all()`
- Migration files: `alembic/versions/` — named `NNNN_<description>.py` with sequential revision IDs
- After any SQLAlchemy model change: `alembic revision --autogenerate -m "<description>"`, then review and run `alembic upgrade head`
- After creating a migration, update `alembic/README` with the new migration run instructions and notes
- `down_revision` must always point to the previous migration — never `None` except the initial
- Production deploy: start command prepends `alembic upgrade head &&` before the server command

---

## Non-Negotiable Rules

- Max **150 lines** per Python file — split if exceeded
- No raw SQL — ORM only
- Strict layering: `API → Service → Repository → ORM`
- No cross-domain imports at Repository or Model level
- No business logic in API routers
- Background jobs must be idempotent
- Auth: `require_role()` at endpoint level; fine-grained checks in Service layer
- Every list endpoint must support standardized pagination, filtering, and sorting
- Sensitive write operations (imports, bulk actions, background triggers) must require an idempotency key
- All user-facing strings in Hebrew (error messages, logs that surface to UI)

---

## Routes

| Type     | Pattern                                                            |
| -------- | ------------------------------------------------------------------ |
| Business | `/api/v1/*`                                                        |
| Auth     | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`              |
| Public   | `GET /`, `GET /health/*`, `GET /info`, `GET /sign/{signing_token}` |

---

## Derived State (never persisted)

- `WorkState`: `WAITING_FOR_WORK | IN_PROGRESS | COMPLETED` — computed in Service layer, never stored
- Signals: `MISSING_DOCS | OVERDUE | READY_FOR_PICKUP | UNPAID_CHARGES | IDLE_BINDER` — computed, not stored

This is the root cause of all in-memory fetch limits below.

---

## Known Architectural Debt (Sprint 10+)

These are intentional, documented constraints — not bugs. Do not work around them without a plan.

| Location                        | Limit                                                            | Behavior when exceeded                   |
| ------------------------------- | ---------------------------------------------------------------- | ---------------------------------------- |
| `dashboard_extended_service.py` | `_ACTIVE_BINDERS_FETCH_LIMIT = 1000` active binders              | Raises `AppError` (HTTP 500)             |
| `dashboard_extended_service.py` | `_UNPAID_CHARGES_FETCH_LIMIT = 500` charges                      | Raises `AppError` (HTTP 500)             |
| `search_service.py`             | `_MIXED_SEARCH_BINDER_LIMIT = 1000` binders                      | Results silently capped                  |
| `search_service.py`             | `_MIXED_SEARCH_CLIENT_LIMIT = 500` clients                       | Results silently capped                  |
| `timeline_service.py`           | `_TIMELINE_BULK_LIMIT = 500` per entity                          | Older events silently truncated          |
| `reports_service.py`            | `_AGING_CHARGE_FETCH_LIMIT = 2000` charges                       | Charges beyond ceiling silently excluded |
| `tax_deadline` repo             | No server-side pagination on global pending list                 | Unbounded DB query                       |
| `binders/work_state`            | Notification check fetches 100 by `client_id`, filters in memory | No binder-scoped query                   |

**Root fix:** persist `work_state` and signals, or push aggregation to SQL. Until then, respect the ceilings.

---

## Infrastructure

### Storage

- Dev: `LocalStorageProvider` (automatic when `APP_ENV=development`) — writes to `./storage/`
- Prod: `S3StorageProvider` (Cloudflare R2) — requires env vars:
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`
- Factory: `get_storage_provider()` in `app/infrastructure/storage.py`

### Notifications

- `NotificationService` — sends via `WhatsAppChannel` first, falls back to email
- Channels are **stubs** — no live delivery. `NOTIFICATIONS_ENABLED=false` in production (`render.yaml`)
- No scheduler wired. No resend UI. No delivery webhook.
- Idempotency: `exists_for_binder_trigger` prevents duplicate sends.

### Deployment

- Platform: Render (`render.yaml`)
- Start: `alembic upgrade head && gunicorn -k uvicorn.workers.UvicornWorker app.main:app`
- Required secrets (set in Render dashboard — never commit): `DATABASE_URL`, `JWT_SECRET`, `CORS_ALLOWED_ORIGINS`
- Optional secrets: `SENDGRID_API_KEY`, `EMAIL_FROM_ADDRESS`, `R2_*`, `INVOICE_PROVIDER_*`

---

## Reference Docs in Repo

| File                           | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `alembic/versions/`            | Migration history                               |
| `render.yaml`                  | Production deploy config and env var list       |
| `app/infrastructure/README.md` | Storage + notification adapter details          |
