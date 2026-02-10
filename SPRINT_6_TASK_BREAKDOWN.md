# SPRINT 6 – TASK BREAKDOWN
## Backend Operational Readiness & UX Enablement

Status: DRAFT (Pending Freeze Approval)  
Linked Spec: SPRINT_6_FORMAL_SPECIFICATION.md  
Depends On: Sprint 1–5 (Frozen)

---

## 1. General Constraints (Applies to All Tasks)

- API → Service → Repository → ORM only
- No raw SQL
- ≤ 150 lines per file
- No breaking changes
- No UI code
- Derived state only (no new persisted status columns)
- SLA logic must remain centralized in SLAService
- Advisor remains super-role

---

## 2. Task Group A – Operational Work State

### Task A1 – Define Work State Derivation
**Goal:** Introduce derived work state for binders.

Actions:
- Create WorkState enum (internal, not persisted)
- Implement derivation logic in service layer

WorkState values:
- waiting_for_work
- in_progress
- completed

Inputs:
- binder.status
- received_at
- notification history
- ready_for_pickup state

Deliverables:
- WorkState derivation method
- Unit tests for each WorkState branch

---

### Task A2 – Expose Work State via API
**Goal:** Make WorkState available to frontend.

Actions:
- Extend binder-related response schemas
- Ensure backward compatibility

Deliverables:
- Updated response schemas
- Regression-safe API output

---

## 3. Task Group B – Operational Signals

### Task B1 – Define Signal Types
**Goal:** Define internal UX signals.

Signals:
- missing_permanent_documents
- near_sla
- overdue
- ready_for_pickup
- unpaid_charges
- idle_binder

Deliverables:
- Signal enum or value object
- Central signal computation entry point

---

### Task B2 – Signal Computation Logic
**Goal:** Compute signals dynamically.

Actions:
- Implement signal derivation in service layer
- Use SLAService for SLA-related signals
- Ensure no persistence

Deliverables:
- SignalService or equivalent
- Unit tests per signal

---

### Task B3 – Attach Signals to API Responses
**Goal:** Make signals consumable by UI.

Actions:
- Attach signals to:
  - Binder responses
  - Dashboard endpoints

Deliverables:
- Updated schemas
- API tests verifying signals

---

## 4. Task Group C – Dashboard Extensions

### Task C1 – Work Queue Endpoint
Endpoint:
GET /dashboard/work-queue
Includes:
- Binder ID
- Client reference
- WorkState
- Signals
- SLA summary

Deliverables:
- Repository query
- Service aggregation
- API router
- Tests

---

### Task C2 – Alerts Endpoint
Endpoint:
GET /dashboard/alerts
Includes:
- Overdue binders
- Near SLA binders
- Missing documents

Deliverables:
- Alert aggregation logic
- SLA-driven filtering
- Tests

---

### Task C3 – Attention Endpoint
Endpoint:
GET /dashboard/attention
Includes:
- Idle binders
- Ready-for-pickup not collected
- Unpaid charges (advisor-only view)

Deliverables:
- Authorization enforcement
- Tests for role restrictions

---

## 5. Task Group D – Unified Client Timeline

### Task D1 – Timeline Aggregation Service
**Goal:** Aggregate all client-related events.

Sources:
- Binder intake
- Binder status logs
- Notifications
- Charges
- Invoices
- Binder returns

Deliverables:
- TimelineService
- Normalized timeline event schema

---

### Task D2 – Timeline API
Endpoint:
GET /clients/{client_id}/timeline
Requirements:
- Chronological ordering
- Pagination support
- Stable event typing

Deliverables:
- API router
- Response schema
- Tests

---

## 6. Task Group E – Search & Filtering

### Task E1 – Unified Search Logic
**Goal:** Provide backend search for UI.

Supported filters:
- Client name
- ID number
- Binder number
- SLA state
- WorkState
- Signals

Deliverables:
- SearchService
- Repository queries
- Pagination support

---

### Task E2 – Search API
Endpoint:
GET /search
Deliverables:
- API router
- Input validation
- Tests

---

## 7. Task Group F – Authorization Refinement

### Task F1 – Action-Level Authorization
**Goal:** Enforce permissions beyond endpoint level.

Rules:
- Secretary:
  - Cannot view charge amounts
  - Cannot trigger payment reminders
- Advisor:
  - Full access

Deliverables:
- Authorization checks in service layer
- Tests verifying forbidden actions

---

## 8. Task Group G – Testing & Validation

### Task G1 – Regression Tests
- Verify Sprint 1–5 behavior unchanged
- Verify no mutation in read-only endpoints

---

### Task G2 – New Feature Tests
Mandatory coverage:
- WorkState derivation
- Signal derivation
- Timeline aggregation
- Dashboard endpoints
- Search filtering
- Authorization boundaries

---

## 9. Completion Checklist

Sprint 6 is complete when:
- All tasks A–G implemented
- No schema drift
- API_CONTRACT.md updated
- All tests pass:
JWT_SECRET=test-secret pytest -q
---

End of Task Breakdown