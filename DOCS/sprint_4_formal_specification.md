# Sprint 4 – Formal Specification

## Status
**FROZEN**

---

## 1. Purpose
Sprint 4 focuses on **operational enablement**. The goal is to turn the system from a stable data platform into a **daily operational assistant** for the tax advisor office.

This sprint deliberately avoids financial automation and advanced UX. It introduces notifications, background processing, and basic document presence management.

---

## 2. In Scope

### 2.1 Notification Engine
The system shall generate and send automated notifications based on predefined operational triggers.

#### Supported Triggers (Frozen)
- Binder received in office
- Binder approaching SLA threshold (e.g. day 75)
- Binder overdue (90+ days)
- Binder ready for pickup
- Manual payment reminder (advisor-triggered)

#### Channels
- WhatsApp (primary)
- Email (fallback)

All notifications must:
- Be persisted in the `notifications` table
- Include a content snapshot
- Reference the related client and binder (if applicable)

---

### 2.2 Background Job
A single daily background job shall be introduced.

Responsibilities:
- Scan all active binders
- Compute SLA state using `SLAService`
- Emit notifications based on triggers

Constraints:
- One job only
- No user-configurable scheduling
- No cron UI
- No raw SQL

---

### 2.3 Permanent Documents – Presence Management

Sprint 4 introduces **document presence tracking**, not full document management.

Supported document types:
- ID copy
- Power of attorney
- Engagement agreement

Capabilities:
- Upload document via API
- Store file via storage abstraction (S3/GCS compatible)
- Mark document as present (`is_present = true`)

Limitations (Frozen):
- No deletion
- No versioning
- No editing
- No client portal access

---

### 2.4 Operational Signals

The system shall expose non-blocking operational indicators:
- Missing permanent documents
- Binder nearing SLA
- Binder overdue

Indicators are advisory only and do not block operations.

---

## 3. User Roles

### Secretary
- Trigger binder intake notifications
- Upload permanent documents
- View operational indicators

### Advisor
- Advisor is a super-role and may perform all Secretary actions
- View full notification history
- Trigger manual payment reminders
- View document presence status

---

## 4. Out of Scope (Frozen)

The following are explicitly excluded from Sprint 4:
- Automated billing or retainers
- SMS notifications
- Client-facing portal
- Dynamic template management
- Reporting or analytics
- UI redesign

---

## 5. Architectural Constraints

The following constraints are mandatory:
- API → Service → Repository → ORM
- Notification logic in Service layer only
- Background jobs must use Services
- No raw SQL
- No file exceeding 150 lines
- Single responsibility per file

---

## 6. Database Impact

- Existing tables (`notifications`, `permanent_documents`) shall be reused
- New columns allowed only if strictly required
- No breaking schema changes

---

## 7. Acceptance Criteria

Sprint 4 is considered complete when:
- Notifications are sent automatically and persisted
- Daily job executes deterministically
- Permanent document presence is trackable
- No Sprint 1–3 behavior is modified
- All tests pass

---

## 8. Freeze Rules

Once approved:
- This document becomes authoritative
- No scope additions without a new sprint
- Any deviation requires formal approval

---

## 9. Approval Checkpoint

Upon approval, this specification shall be marked:

**Status: FROZEN**

---

*End of Sprint 4 Formal Specification*
