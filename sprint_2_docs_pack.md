# SPRINT_2_OVERVIEW.md

## Sprint Goal
Deliver operational and business value by exposing SLA, overdue logic, and management-level insights via API.

## In Scope
- SLA & overdue logic (derived, not persisted)
- Dashboard overview API
- Operational binder queries
- Binder history (audit) read endpoint
- Authorization tightening using existing role helpers

## Out of Scope
- UI / frontend
- New roles or auth redesign
- Cron jobs or background workers
- New DB columns for SLA

## Definition of Done
- Overdue binders can be queried via API
- One dashboard endpoint provides system snapshot
- SLA logic is centralized and reused
- Audit history is readable via API
- Authorization is consistent and enforced
- No file exceeds 150 lines (markdown excluded)

---

# DOMAIN_RULES.md

## Binder Lifecycle
Statuses:
- RECEIVED
- IN_PROGRESS
- RETURNED

## Open Binder
A binder is considered OPEN if:
status != RETURNED

## Overdue Binder
A binder is OVERDUE if:
- today > expected_return_at
- status != RETURNED

## Derived Fields (Not Persisted)
- is_overdue: boolean
- days_overdue: integer >= 0

## Rules
- Derived fields are calculated at query time
- No SLA fields are stored in the database
- One shared logic must be reused across endpoints

---

# API_CONTRACT_SPRINT_2.md

## Dashboard
### GET /dashboard/overview
Authorization: ADMIN, MANAGER

Response:
{
  "total_clients": number,
  "active_binders": number,
  "overdue_binders": number,
  "binders_due_today": number,
  "binders_due_this_week": number
}

---

## Binders

### GET /binders/open
### GET /binders/overdue
### GET /binders/due-today

Common:
- Pagination
- Ordering
- No ORM leakage

---

### GET /binders/{id}/history
Authorization: read-only, role-guarded

Response:
- old_status
- new_status
- changed_by
- changed_at
- notes

---

### GET /clients/{id}/binders
Authorization: operational roles

---

# SPRINT_2_TASKS.md

## P0 – Must Have
- Central SLA / overdue logic
- Dashboard overview endpoint
- Overdue binders endpoint
- Authorization enforcement on critical routes

## P1 – Important
- Binder history endpoint
- Client -> binders relationship API
- Pagination and ordering support

## P2 – Nice to Have
- Export-ready response shapes
- Basic metrics (average return time)

---

# AUTHORIZATION_MATRIX.md

| Endpoint | ADMIN | MANAGER | OPERATOR |
|--------|-------|---------|----------|
| /dashboard/overview | ✅ | ✅ | ❌ |
| /binders/overdue | ✅ | ✅ | ✅ |
| /binders/{id}/history | ✅ | ✅ | ✅ |
| /clients/{id}/binders | ✅ | ✅ | ✅ |

