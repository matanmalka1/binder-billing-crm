# Backend Deferred Capabilities Specification

_Binder & Billing CRM_

**Status:** DRAFT – Deferred (Post Sprint 7)  
**Audience:** Backend / Architecture  
**Purpose:** Document backend capabilities intentionally not implemented yet, but required for a mature, production-grade system.

---

## 1. User Management (Minimal, Controlled)

**Goal:** Enable operational control, auditability, and basic lifecycle management of system users.

**Scope (minimal by design):**
- Edit user profile:
  - Full name
  - Phone number
  - Role (Advisor / Secretary)
- Activate / deactivate user
- Password reset / token invalidation
- Login & action audit logs

**Explicit non-goals:**
- No self-registration
- No multi-tenant user groups
- No complex RBAC UI
- No external IAM integration

**Rationale:** Current usage is limited to ~2 internal users. Functionality must exist, but complexity must remain low.

---

## 2. Fine-Grained Permissions (Beyond Role)

**Goal:** Allow future restriction of specific actions without role explosion.

**Examples:**
- Secretary can view charges but cannot issue or cancel
- Advisor can trigger payment reminders
- Read vs write separation per resource

**Constraints:**
- Permission checks enforced at service layer
- No permission persistence UI required initially
- No policy engine (simple rule mapping)

---

## 3. Advanced Business Workflows

**Goal:** Support multi-step, stateful business flows beyond CRUD.

**Examples:**
- Client onboarding workflow
- Binder lifecycle escalation flow
- Charge → invoice → reminder → follow-up chain

**Characteristics:**
- Workflow = derived state, not persisted FSM
- Steps observable via timeline
- Abort / retry allowed

---

## 4. Advanced Billing Capabilities

**Goal:** Extend Sprint 3 billing into a real operational billing system.

**Deferred features:**
- Partial payments
- Payment reconciliation
- Credit notes / refunds
- Recurring retainers
- Billing summaries & exports

**Constraints:**
- No automated charging yet
- No accounting system coupling
- Manual advisor-triggered actions only

---

## 5. Advanced Observability

**Goal:** Improve operational insight and debugging without external APM.

**Deferred capabilities:**
- Structured audit logs per entity
- Correlation IDs across services/jobs
- Failure counters (jobs, notifications)
- Basic metrics (counts, latencies)

**Explicit non-goals:**
- No Prometheus/Grafana
- No external tracing tools

---

## 6. Job Management & Control

**Goal:** Make background jobs observable and controllable.

**Deferred features:**
- Job execution history
- Manual re-run
- Disable/enable jobs
- Failure retries visibility

**Constraints:**
- Jobs remain server-side only
- No scheduler UI required initially

---

## 7. Bulk Operations

**Goal:** Enable operational efficiency for high-volume actions.

**Examples:**
- Bulk binder intake
- Bulk status transitions
- Bulk notifications
- Bulk charge creation

**Constraints:**
- Explicit confirmation required
- Async execution preferred
- Audit trail mandatory

---

## 8. API Versioning Strategy

**Goal:** Allow backward compatibility as frontend and integrations evolve.

**Deferred capabilities:**
- `/api/v2` namespace
- Deprecation policy
- Versioned schemas

**Constraints:**
- No breaking changes retroactively
- v1 remains supported until explicit sunset

---

## 9. Explicitly Out of Scope (For Now)

- Multi-tenant support
- External user portal
- Real-time WebSockets
- BI / Analytics dashboards
- Multi-language support
- Plugin architecture

---

## 10. Status Summary

| Area | Status |
|---|---|
| Core CRM | Implemented |
| Billing (basic) | Implemented |
| Notifications | Implemented |
| Jobs | Implemented (basic) |
| User Management | Deferred |
| Permissions | Deferred |
| Workflows | Deferred |
| Advanced Billing | Deferred |
| Observability | Deferred |
| Bulk Ops | Deferred |
| API Versioning | Deferred |

This document is declarative only.
No implementation is implied until explicitly scheduled into a future sprint.
