# Sprint 4 – Task Breakdown

## Phase 1 – Notification Engine
- Create NotificationService
- Implement channel abstraction (WhatsApp / Email)
- Persist notifications with content snapshots
- Ensure non-blocking behavior on send failure

---

## Phase 2 – Background Job
- Implement a single daily job service
- Scan all active binders
- Evaluate SLA state using SLAService
- Emit notifications based on defined triggers
- Add idempotency safeguards to prevent duplicate notifications

---

## Phase 3 – Permanent Documents
- Implement storage abstraction (S3 / GCS compatible)
- Create PermanentDocumentsService
- Implement document upload API endpoints
- Enforce supported document types only
- Mark document presence (is_present = true)

---

## Phase 4 – Operational Signals
- Compute missing document indicators per client
- Compute SLA proximity indicators per binder
- Compute overdue indicators (derived, not stored)
- Ensure all signals are advisory (non-blocking)

---

## Phase 5 – Tests & Validation
- Add unit tests for services
- Add integration tests for APIs
- Add background job tests
- Add regression tests for Sprint 1–3 functionality

---

*End of Sprint 4 Task Breakdown*