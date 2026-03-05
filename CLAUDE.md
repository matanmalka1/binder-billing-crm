# CLAUDE.md — Binder & Billing CRM (Backend)

## Assistant Behavior

- No greetings, affirmations, or filler ("Sure!", "Great question", "I hope this helps")
- Never repeat the user's prompt back to them
- Skip explanations unless explicitly requested
- Think step-by-step internally, but only output the final result unless reasoning is requested
- Prefer code and bullet points over prose
- Get it right the first time — verify against existing patterns before generating

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
JWT_SECRET=test-secret pytest -q
```

---

## Stack

- FastAPI, SQLAlchemy ORM (no raw SQL), Pydantic v2
- Dev: SQLite; Prod: PostgreSQL
- Migrations: Alembic (`alembic/`) — `Base.metadata.create_all()` is NOT used
- Auth: JWT HS256, `token_version` invalidation on User model

---

## Domain Structure (20 domains + 5 infra)

Routed domains (have `api/` router): `advance_payments`, `annual_reports`, `authority_contact`, `binders`, `charge`, `clients`, `correspondence`, `dashboard`, `health`, `permanent_documents`, `reminders`, `reports`, `search`, `signature_requests`, `tax_deadline`, `timeline`, `users`, `vat_reports`

Internal-only domains (no HTTP router): `invoice`, `notification` — full layer stack, used as services by other domains.

Shared utility: `common/` — repositories only, no layers.

Every routed domain follows exactly:

```
app/<domain>/
├── api/           # Routers — request/response only
├── services/      # All business logic; cross-domain entry point
├── repositories/  # ORM queries only
├── schemas/       # Pydantic v2 (no ORM coupling)
└── models/        # SQLAlchemy ORM declarations
```

Infra (`core/`, `utils/`, `infrastructure/`, `middleware/`, `actions/`) — no layer structure.

---

## Migrations (Alembic)

- All schema changes go through Alembic — never modify the DB directly or use `create_all()`
- Migration files live in `alembic/versions/` — named `NNNN_<description>.py` with sequential revision IDs
- After changing any SQLAlchemy model: `alembic revision --autogenerate -m "<description>"`, then review and run `alembic upgrade head`
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

---

## Routes

| Type | Pattern |
|---|---|
| Business | `/api/v1/*` |
| Auth | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` |
| Public | `GET /`, `GET /health/*`, `GET /info`, `GET /sign/{signing_token}` |

---

## Derived State (never persisted)

- `WorkState`: `WAITING_FOR_WORK | IN_PROGRESS | COMPLETED` — computed in Service
- Signals: `MISSING_DOCS | OVERDUE | READY_FOR_PICKUP | UNPAID_CHARGES | IDLE_BINDER` — computed, not stored

---

## Known Issues

No current known issues.
