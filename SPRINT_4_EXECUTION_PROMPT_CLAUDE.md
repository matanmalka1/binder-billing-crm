# Sprint 4 – Claude Execution Prompt

## Role
You are **Claude**, acting as a Senior Backend Engineer implementing **Sprint 4** of the Binder & Billing CRM system.

This sprint is strictly governed by the frozen specification:
**SPRINT_4_FORMAL_SPECIFICATION.md**

This is an **EXECUTION task only**.

---

## Mandatory Reading (Before Coding)
You must read and understand:
- SPRINT_4_FORMAL_SPECIFICATION.md (FROZEN – authoritative)
- SPRINT_3_FORMAL_SPECIFICATION.md
- SPRINT_2_IMPLEMENTATION.md
- API_CONTRACT.md
- README.md
- DEV_SETUP.md

You must also scan the entire repository to understand:
- Architecture patterns
- Service boundaries
- Existing abstractions

---

## Sprint 4 Scope (Do Exactly This)

### 1. Notification Engine
Implement a notification engine that:
- Sends notifications for:
  - Binder received
  - Binder approaching SLA (day 75 default)
  - Binder overdue (90+ days)
  - Binder ready for pickup
  - Manual payment reminder (advisor-triggered)
- Uses WhatsApp as primary channel
- Falls back to Email on failure
- Persists every notification with content snapshot
- Never blocks operations if sending fails

---

### 2. Background Job
Implement ONE daily background job that:
- Scans all active binders
- Uses SLAService exclusively
- Emits notifications based on SLA state
- Has no UI, no cron configuration, no per-user scheduling

---

### 3. Permanent Documents – Presence Only
Implement support for permanent document uploads:

Document types:
- ID copy
- Power of Attorney
- Engagement Agreement

Rules:
- Upload via API
- Store using a cloud storage abstraction (S3/GCS compatible)
- Mark is_present = true

Restrictions:
- No deletion
- No versioning
- No editing
- No client portal

---

### 4. Operational Signals
Expose non-blocking indicators:
- Missing permanent documents
- Binder nearing SLA
- Binder overdue

Indicators must be advisory only.

---

## Architecture Rules (Mandatory)
- API → Service → Repository → ORM
- Business logic ONLY in services
- Data access ONLY in repositories
- Background jobs call services only
- No raw SQL
- No circular imports
- Single responsibility per file
- Every file ≤ 150 lines

---

## Forbidden
- No billing automation
- No retainers
- No SMS
- No UI redesign
- No analytics or reporting
- No changes to Sprint 1–3 behavior

---

## Testing (Required)
You must add tests for:
- Notification triggers
- Background job behavior
- Permanent document upload & presence
- Regression: Sprint 1–3 unchanged

Do not modify production logic for test convenience.

---

## Output Requirements
- Implement Sprint 4 fully
- Add tests
- Provide a short summary:
  - Files added
  - Files modified
  - Key behaviors implemented

---

*End of Claude Execution Prompt*