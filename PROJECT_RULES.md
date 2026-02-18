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

- Maximum 150 lines per Python file
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

The application is organized into independent Domains (e.g. `advance_payments`, `binders`). Each domain must strictly implement the following sub-structure:

- **API Layer** (`/api`)
  - Request/response handling only (FastAPI routers)
  - Authorization guards
  - No business decisions

- **Service Layer** (`/services`)
  - All business logic and state derivation
  - Authorization decisions at action level
  - The only entry point for cross-domain communication

- **Repository Layer** (`/repositories`)
  - Data access only (SQLAlchemy/ORM queries)
  - No business rules or cross-domain data fetching

- **Schemas Layer** (`/schemas`)
  - Pydantic models for validation and serialization
  - Strict separation from ORM models

- **ORM Models** (`/models`)
  - Data structure / SQLAlchemy declarations only
  - No behavior or logic

### 4. Data & State Rules

#### 4.1 Derived State Policy

The following must **never** be persisted:

- SLA state
- Overdue / near-SLA status
- WorkState
- Operational signals

All such states are computed dynamically.

#### 4.2 SLA Rules

- SLA logic lives in `SLAService`
- SLA is derived from timestamps only
- No SLA status columns are allowed
- No background job may persist SLA state

### 5. Operational Concepts

#### 5.1 WorkState

- WorkState is derived, not stored
- Exists solely to support operational UX
- Must be deterministic from system state

#### 5.2 Signals

- Signals are internal, advisory-only indicators
- Signals do not block actions
- Signals are not notifications
- Signals are computed, not stored

### 6. Authorization Philosophy

- **Advisor** is a super-role
- **Secretary** is operational-only
- Authorization is enforced at:
  - Endpoint level
  - Service/action level
- UI must **never** implement business authorization logic

### 7. Notifications & Jobs

- Notifications must persist content snapshots
- Notification emission must be idempotent
- Daily jobs must:
  - Use `SLAService` for SLA logic
  - Avoid duplicate notifications
  - Never mutate derived state

### 8. Database & Migrations

- Early development: **no migrations**.  
  Schema is created from ORM models in `APP_ENV=development`.

### 9. Sprint Discipline

- Every sprint requires:
  - Formal specification
  - Explicit freeze
- Out-of-scope features are forbidden
- Deviations require explicit approval
- Completed sprints are immutable

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

**End of Rules**'
