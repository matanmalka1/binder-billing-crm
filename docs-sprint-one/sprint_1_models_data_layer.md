# Binder & Billing CRM
## Sprint 1 Models & Data Layer

---

## 1. Purpose
Define Sprint 1 model contracts and repository behavior for:
- `users`
- `clients`
- `binders`
- `binder_status_logs`

All primary keys use regular integer auto-increment IDs.

---

## 2. Data Conventions
1. PK type: `INTEGER` auto-increment (`1, 2, 3, ...`).
2. Timestamps stored in UTC.
3. No hard deletes; use status fields for lifecycle.
4. FK references use integer IDs.
5. Validation happens at both API and data layer for critical constraints.

---

## 3. Model Contracts
## 3.1 User
Fields:
- `id: int`
- `full_name: str`
- `email: str`
- `phone: str | null`
- `role: "advisor" | "secretary"`
- `is_active: bool`
- `created_at: datetime`
- `last_login_at: datetime | null`

## 3.2 Client
Fields:
- `id: int`
- `full_name: str`
- `id_number: str`
- `client_type: "osek_patur" | "osek_murshe" | "company" | "employee"`
- `status: "active" | "frozen" | "closed"`
- `primary_binder_number: str | null`
- `phone: str | null`
- `email: str | null`
- `notes: str | null`
- `opened_at: date`
- `closed_at: date | null`

## 3.3 Binder
Fields:
- `id: int`
- `client_id: int`
- `binder_number: str`
- `received_at: date`
- `expected_return_at: date`
- `returned_at: date | null`
- `status: "in_office" | "ready_for_pickup" | "returned" | "overdue"`
- `received_by: int`
- `returned_by: int | null`
- `pickup_person_name: str | null`
- `notes: str | null`

## 3.4 BinderStatusLog
Fields:
- `id: int`
- `binder_id: int`
- `old_status: str`
- `new_status: str`
- `changed_by: int`
- `changed_at: datetime`
- `notes: str | null`

---

## 4. Repository Interfaces
## 4.1 ClientRepository
Methods:
- `create(payload) -> Client`
- `get_by_id(client_id: int) -> Client | null`
- `list(filters, page, page_size) -> list[Client]`
- `update(client_id: int, payload) -> Client`
- `set_status(client_id: int, status) -> Client`

## 4.2 BinderRepository
Methods:
- `receive(payload) -> Binder`
- `get_by_id(binder_id: int) -> Binder | null`
- `list_active(filters) -> list[Binder]`
- `mark_ready_for_pickup(binder_id: int, user_id: int) -> Binder`
- `return_binder(binder_id: int, pickup_person_name: str, user_id: int) -> Binder`
- `mark_overdue(reference_date: date) -> int`

## 4.3 BinderStatusLogRepository
Methods:
- `append(binder_id: int, old_status: str, new_status: str, changed_by: int, notes: str | null) -> BinderStatusLog`
- `list_by_binder(binder_id: int) -> list[BinderStatusLog]`

---

## 5. Transaction Rules
1. `receive` binder must insert binder and initial status log in one transaction.
2. `return_binder` must update binder and insert status log in one transaction.
3. If status log insert fails, binder status change is rolled back.

---

## 6. Query & Index Guidance
1. Index `binders.status`, `binders.received_at`, `binders.expected_return_at`.
2. Index `binders.client_id` and `binder_status_logs.binder_id`.
3. Keep unique `clients.id_number`, `users.email`.
4. Enforce one active binder per `binder_number` with partial unique index.

---

## 7. Test Matrix (Sprint 1)
1. Creates records with integer IDs that increment sequentially.
2. Rejects duplicate `users.email` and `clients.id_number`.
3. Prevents returning binder without `pickup_person_name`.
4. Correctly flags overdue binders after 90 days.
5. Writes status logs for every status change.

---

*End of Sprint 1 Models & Data Layer*
