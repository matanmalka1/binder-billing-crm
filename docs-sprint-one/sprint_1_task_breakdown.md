# Binder & Billing CRM
## Sprint 1 Task Breakdown

---

## 1. Sprint Goal
Deliver the first usable backend slice for:
- User authentication and role checks
- Client management
- Binder intake/return lifecycle
- Core dashboard counters

Sprint duration: 2 weeks

---

## 2. Scope for Sprint 1
Included:
- DB migrations for `users`, `clients`, `binders`, `binder_status_logs`
- Data layer (models + repositories)
- API endpoints for clients and binders
- 90-day overdue calculation
- Basic dashboard summary API

Excluded:
- Billing (`charges`, `invoices`)
- Notification sending integrations
- File upload for permanent documents

---

## 3. Work Breakdown
## 3.1 Foundation
1. Create project structure and environment config.
Acceptance criteria: app boots locally and health endpoint returns `200`.

2. Add auth middleware and role guard (`advisor`, `secretary`).
Acceptance criteria: protected routes reject unauthenticated requests.

## 3.2 Database & Migrations
1. Create initial migration for users/clients/binders/logs tables.
Acceptance criteria: migration runs up/down without errors.

2. Add indexes and constraints:
- unique email (`users.email`)
- unique ID number (`clients.id_number`)
- partial uniqueness for active binder by `binder_number`
Acceptance criteria: duplicate inserts fail as expected.

## 3.3 Models & Repositories
1. Implement models aligned to schema using integer auto-increment IDs.
Acceptance criteria: create/read/update flows for each model pass tests.

2. Implement repository methods for:
- clients: create, get_by_id, list, update_status
- binders: receive, return, mark_overdue, list_active
- binder_status_logs: append_status_change
Acceptance criteria: repository tests cover happy path and key failures.

## 3.4 API Endpoints
1. Clients API:
- `POST /api/v1/clients`
- `GET /api/v1/clients`
- `GET /api/v1/clients/{id}`
- `PATCH /api/v1/clients/{id}`
Acceptance criteria: request validation + correct status codes.

2. Binders API:
- `POST /api/v1/binders/receive`
- `POST /api/v1/binders/{id}/return`
- `GET /api/v1/binders`
Acceptance criteria: return flow requires `pickup_person_name`.

3. Dashboard API:
- `GET /api/v1/dashboard/summary`
Acceptance criteria: returns counts for in-office, ready, overdue.

## 3.5 Business Rules
1. Calculate `expected_return_at = received_at + 90 days`.
2. Overdue if current date is after `expected_return_at` and not returned.
3. Intake is never blocked by debt/document warnings.
Acceptance criteria: rule tests pass with deterministic dates.

## 3.6 QA & Readiness
1. Unit tests for services and repositories.
2. Integration tests for critical endpoints.
3. API contract sanity check against `api_contracts.md`.
Acceptance criteria: CI test pass rate 100% for sprint scope.

---

## 4. Definition of Done
1. All sprint-scope migrations merged and reversible.
2. All sprint endpoints implemented and documented.
3. All IDs are integer auto-increment values (1, 2, 3...).
4. Core business rules covered by automated tests.
5. Demo script ready for intake, return, and dashboard flow.

---

*End of Sprint 1 Task Breakdown*
