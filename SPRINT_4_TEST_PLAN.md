# Sprint 4 – Test Plan

## Objective
Ensure Sprint 4 operational features are correct, stable, and do not regress Sprint 1–3 behavior.

---

## 1. Notification Tests
- Notification created on binder receive
- SLA-based notifications (approaching / overdue)
- Ready-for-pickup notification
- Content snapshot persisted
- Failure does not block workflow

---

## 2. Background Job Tests
- Daily job scans binders
- SLAService used exclusively
- Correct notifications emitted
- Idempotency (no duplicate notifications)

---

## 3. Permanent Documents Tests
- Upload document sets is_present=true
- Valid document types only
- No delete/update endpoints exist
- Correct client association

---

## 4. Authorization Tests
- Secretary: upload documents, operational triggers
- Advisor: manual reminders, history access
- Unauthorized access blocked

---

## 5. Regression Tests
- Binder lifecycle unchanged
- SLA logic unchanged
- Billing (Sprint 3) untouched

---

## Completion Criteria
Sprint 4 tests pass when:
- All new tests pass
- All existing tests pass
- No flaky behavior detected

---

*End of Sprint 4 Test Plan*