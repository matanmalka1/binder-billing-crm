**Status:** ACTIVE
**Applies To:** Entire Codebase

### 1. Purpose

This document defines the non-negotiable engineering, architectural, and operational rules of the Binder & Billing CRM project.

Its purpose is to:

- Preserve long-term architectural integrity
- Prevent scope creep and hidden regressions
- Ensure consistency across sprints and contributors
- Serve as the highest-level engineering contract

If a conflict arises between this document and other documentation, **this document prevails** unless explicitly amended.

### 2. Non-Negotiable Engineering Rules

The following rules must not be violated without explicit approval:

- **Maximum 150 lines per Python file** — files that grow beyond this must be split; existing overages are tracked debt
- No raw SQL (ORM-only access)
- Strict layering within each Domain:
  **API → Service → Repository → ORM**
- No cross-domain imports at the Repository or Model level
- No business logic in API routers
- No silent breaking changes
- All background jobs must be **idempotent**
- Health endpoints must be deterministic and safe

### 3. Architecture Rules

#### 3.1 Domain-Based Structure

The application is organized into 25 independent business domains (e.g. `advance_payments`, `binders`, `annual_reports`) plus 5 infrastructure modules (`core`, `utils`, `infrastructure`, `middleware`, `actions`).

Each business domain must strictly implement the following sub-structure:

- **API Layer** (`/api`)
  - Request/response handling only (FastAPI routers)
  - Authorization guards via `require_role()` dependency
  - No business decisions

- **Service Layer** (`/services`)
  - All business logic and state derivation
  - Authorization decisions at action level
  - The only entry point for cross-domain communication

- **Repository Layer** (`/repositories`)
  - Data access only (SQLAlchemy/ORM queries)
  - No business rules or cross-domain data fetching

- **Schemas Layer** (`/schemas`)
  - Pydantic v2 models for validation and serialization
  - Strict separation from ORM models
  - Request models: `*CreateRequest` / `*Request`
  - Response models: `*Response`, `*ListResponse`

- **ORM Models** (`/models`)
  - Data structure / SQLAlchemy declarations only
  - No behavior or logic
  - Enums defined alongside their models

#### 3.2 Infrastructure Modules

These modules are not business domains and do not follow the full layer structure:

- **`core/`** — Centralized exception handlers, logging, env validation
- **`utils/`** — Shared utilities (time helpers, etc.)
- **`infrastructure/`** — External service stubs (WhatsApp, Email, S3)
- **`middleware/`** — FastAPI middleware (e.g. RequestIDMiddleware)
- **`actions/`** — UI action metadata and contracts

#### 3.3 API Routes

- All business routes: `/api/v1/*`
- Public routes: `GET /`, `GET /health/*`, `GET /info`, `GET /sign/{signing_token}`
- Auth routes: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`

### 4. Data & State Rules

#### 4.1 Derived State Policy

The following must **never** be persisted:

- WorkState
- Operational signals

All such states are computed dynamically in the Service layer.

### 5. Operational Concepts

#### 5.1 WorkState

- WorkState is derived, not stored
- Exists solely to support operational UX
- Must be deterministic from system state
- Values: `WAITING_FOR_WORK` | `IN_PROGRESS` | `COMPLETED`

#### 5.2 Signals

- Signals are internal, advisory-only indicators
- Signals do not block actions
- Signals are not notifications
- Signals are computed, not stored
- Known signals: `MISSING_DOCS`, `OVERDUE`, `READY_FOR_PICKUP`, `UNPAID_CHARGES`, `IDLE_BINDER`

### 6. Authorization Philosophy

- **Advisor** is a super-role with full access
- **Secretary** is operational-only
- Authorization is enforced at:
  - Endpoint level via `require_role()` dependency factory
  - Service/action level for fine-grained decisions
- Token invalidation via `token_version` field on the User record
- UI must **never** implement business authorization logic

### 7. Notifications & Jobs

- Notifications must persist content snapshots
- Notification emission must be idempotent
- Daily jobs must:
  - Avoid duplicate notifications
  - Never mutate derived state

### 8. Database & Migrations

- Development (`APP_ENV=development`): schema auto-created from ORM models via `Base.metadata.create_all()`. No migration tooling.
- Production: PostgreSQL. Migrations must be managed explicitly before any schema change is deployed.
- ORM is the single source of truth for schema; no schema changes outside of model files.

### 9. Sprint Discipline

- Every sprint requires:
  - Formal specification
  - Explicit freeze
- Out-of-scope features are forbidden
- Deviations require explicit approval
- Completed sprints are immutable (Sprints 1–9 are frozen)

### 10. What This Project Is NOT

This project is explicitly **not**:

- A general-purpose CRM
- A billing automation platform
- A client-facing portal (unless specified)
- Analytics-first
- UI-driven

### 11. Amendment Policy

This document may only be amended by:

- Explicit decision
- Documented change
- Versioned update

**End of Rules**
