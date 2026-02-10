# SPRINT 6 – FORMAL SPECIFICATION
## Operational Readiness & UX Enablement (Backend)

Status: FROZEN  
Applies To: Binder & Billing CRM  
Depends On: Sprint 1–5 (Frozen)

---

## 1. Purpose

Sprint 6 prepares the system for frontend development by completing
all backend capabilities required for a clean, thin, and deterministic UI.

This sprint **does not introduce UI**, but ensures:
- All operational states are computable via API
- All UX-relevant signals are available
- No frontend business logic will be required later

Sprint 6 is strictly additive and introduces **no breaking changes**.

---

## 2. Guiding Principles

- Backend-first UX
- Derived state over persisted state
- No duplication of logic in frontend
- API → Service → Repository → ORM enforced
- SLA logic remains centralized in SLAService
- No new roles introduced
- Advisor remains super-role

---

## 3. In Scope

### 3.1 Operational Work State (Derived)

Introduce a **derived operational work state** for binders.

WorkState is NOT persisted.

Possible values:
- `waiting_for_work`
- `in_progress`
- `completed`

Derived from:
- binder.status
- received_at
- ready_for_pickup
- notification history
- (future) report completion marker

Purpose:
- Distinguish “binder is here” vs “binder is being worked on”
- Enable clear work queues in UI

---

### 3.2 Operational Signals (Internal, Non-Blocking)

Signals are **internal UX indicators**, not notifications.

Signals are computed dynamically and never persisted.

Supported signals:
- `missing_permanent_documents`
- `near_sla`
- `overdue`
- `ready_for_pickup`
- `unpaid_charges`
- `idle_binder`

Signals:
- Do NOT block actions
- Do NOT emit messages
- Are advisory only

---

### 3.3 Dashboard Extensions (API Only)

New dashboard endpoints to support real operational views.

Endpoints:
- `GET /dashboard/work-queue`
- `GET /dashboard/alerts`
- `GET /dashboard/attention`

Each endpoint returns structured, sortable lists
with derived SLA state, work state, and signals.

---

### 3.4 Unified Client Timeline

Provide a single chronological timeline per client.

Endpoint:
GET /clients/{client_id}/timeline
Timeline aggregates:
- Binder intake
- Binder status changes
- Notifications
- Charges
- Invoices
- Binder return

Sorted descending by timestamp.

Purpose:
- Enable “Client 360°” view in UI
- Eliminate frontend data stitching

---

### 3.5 Search & Filtering (Backend)

Introduce a unified search endpoint.

Endpoint:
GET /search
Supported filters:
- Client name
- Client ID number
- Binder number
- SLA state
- Work state
- Signals

Pagination required.

---

### 3.6 Fine-Grained Authorization (Action-Level)

Authorization is refined at **action level**, not role level.

Rules:
- Advisor: full access
- Secretary:
  - No access to financial values
  - Cannot trigger payment reminders
  - Cannot view charge amounts
  - Can view operational signals only

No new roles introduced.

---

## 4. Out of Scope (Explicitly Forbidden)

- UI / Frontend code
- Client portal
- Automated billing or payments
- New notification channels
- Analytics or reporting exports
- Role expansion
- Schema changes not strictly required

---

## 5. Data & Schema Rules

- No new persisted status columns
- No duplication of SLA logic
- No mutation in read-only endpoints
- Signals and work states are derived only
- Existing tables may be read, not modified

---

## 6. API Contract Rules

- All new endpoints must be documented in API_CONTRACT.md
- Existing endpoints must remain unchanged
- Response shapes must be stable and deterministic
- Errors must conform to centralized exception handling

---

## 7. Testing Requirements

Mandatory:
- Full regression for Sprint 1–5
- Tests for:
  - Work state derivation
  - Signal derivation
  - Timeline aggregation
  - Search filtering
  - Authorization boundaries

Prohibited:
- Snapshot-based UI assumptions
- Time-dependent flaky tests

---

## 8. Deliverables

- `SPRINT_6_FORMAL_SPECIFICATION.md` (this document)
- Updated `API_CONTRACT.md`
- New tests only where required
- No breaking changes
- Clean git history

---

## 9. Freeze Rules

Once frozen:
- No scope expansion
- No additional signals
- No role changes
- No schema changes
- Any deviation requires formal amendment

---

## 10. Sprint 6 Completion Criteria

Sprint 6 is complete when:
- All endpoints return deterministic data
- UI can be built without adding logic
- SLA logic remains single-source
- All tests pass
- Codebase remains production-stable

---

End of Specification
