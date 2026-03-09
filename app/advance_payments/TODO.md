## [P2] 3.6 — Progress Bar גביה (Collection Rate %)
**Status:** MISSING
**Gap:** `collection_rate` percentage (paid / expected × 100) is not computed anywhere; overview returns raw payment list only.
**Files to touch:**
- `app/advance_payments/services/advance_payment_service.py` — compute `collection_rate`, `total_expected`, `total_paid` in overview aggregation
- `app/advance_payments/schemas/advance_payment.py` — add `OverviewKPIResponse` or extend existing overview schema with KPI fields
- `app/advance_payments/api/advance_payments_overview.py` — return KPI fields alongside list
**Acceptance criteria:** Overview endpoint returns `collection_rate` (float 0–100), `total_expected`, `total_paid` computed for the filtered period.

---

## [P2] 3.12 — גרף עמודות (Monthly Chart Data)
**Status:** MISSING
**Gap:** No endpoint returns monthly aggregated `paid`/`expected`/`overdue` amounts suitable for a bar chart.
**Files to touch:**
- `app/advance_payments/api/advance_payments_overview.py` — add `GET /advance-payments/chart?client_id=&year=` endpoint
- `app/advance_payments/repositories/advance_payment_repository.py` — add `monthly_chart_data(client_id, year)` query returning 12 monthly rows
- `app/advance_payments/services/advance_payment_service.py` — add `get_chart_data()` service method
- `app/advance_payments/schemas/advance_payment.py` — add `MonthlyChartRow` and `ChartDataResponse` schemas
**Acceptance criteria:** Endpoint returns array of 12 objects `{month, expected_amount, paid_amount, overdue_amount}` for the given year.

---

## [P2] 3.5 — KPI שנתי (Annual KPI Cards)
**Status:** PARTIAL
**Gap:** Overview provides a filtered list but no computed KPI aggregates (`collection_rate`, `total_charged`, `on_time_count`, `late_count`).
**Files to touch:**
- `app/advance_payments/services/advance_payment_service.py` — add `get_annual_kpis(client_id, year)` method
- `app/advance_payments/schemas/advance_payment.py` — add `AnnualKPIResponse` schema
- `app/advance_payments/api/advance_payments_overview.py` — add `GET /advance-payments/kpi?client_id=&year=` endpoint
**Acceptance criteria:** KPI endpoint returns `total_expected`, `total_paid`, `collection_rate`, `overdue_count`, `on_time_count` for the year.

---

## [P2] 3.4 — עמודת הפרש (Delta Calculation)
**Status:** PARTIAL
**Gap:** `expected_amount` and `paid_amount` fields both exist, but `delta = expected − paid` is not computed in the service or returned by the API.
**Files to touch:**
- `app/advance_payments/schemas/advance_payment.py` — add `delta: float` computed field (or add to response schema)
- `app/advance_payments/services/advance_payment_service.py` — compute `delta` when building response objects
**Acceptance criteria:** Each payment object in list/overview responses includes `delta = expected_amount − paid_amount`.

---

## [P2] 3.10 — פעולות שורה — מחיקה (Delete Advance Payment)
**Status:** PARTIAL
**Gap:** Update endpoint exists but there is no `DELETE /advance-payments/{id}` endpoint.
**Files to touch:**
- `app/advance_payments/api/advance_payments.py` — add `DELETE /advance-payments/{payment_id}` (ADVISOR only)
- `app/advance_payments/repositories/advance_payment_repository.py` — add `delete(payment_id)` method
- `app/advance_payments/services/advance_payment_service.py` — add `delete_payment(payment_id, actor)` method
**Acceptance criteria:** `DELETE /advance-payments/{id}` removes the record (hard delete or soft-delete with `is_deleted`) and returns 204.

---

## [P3] 3.2 — חישוב מקדמה אוטומטי (Automated Advance Calculation)
**Status:** PARTIAL
**Gap:** Suggestion is based on prior-year VAT × `advance_rate`; real-time turnover × rate calculation from current-year data is not implemented.
**Files to touch:**
- `app/advance_payments/services/advance_payment_calculator.py` — add `calculate_from_turnover(client_id, year)` using current-year income if available
**Acceptance criteria:** `GET /advance-payments/suggest` accepts `?method=turnover` and returns suggestion derived from current-year revenue × statutory rate when current-year VAT data exists.

---

## [P3] 3.3 — סטטוס תשלום — FUTURE (Future Status)
**Status:** PARTIAL
**Gap:** Payment statuses are PENDING/PAID/PARTIAL/OVERDUE; a `FUTURE` status for not-yet-due months is not a formal enum value.
**Files to touch:**
- `app/advance_payments/models/advance_payment.py` — add `FUTURE` to status enum (or handle via due_date < today logic in service)
- `alembic/versions/` — migration if enum is DB-native
**Acceptance criteria:** Payments with `due_date > today` are returned as status `FUTURE` or `PENDING`, clearly distinguishable in the API response.

---

## [P3] 3.9 — מודאל הוספת מקדמה — Notes (Payment Notes Field)
**Status:** PARTIAL
**Gap:** Create/update schema has no `notes` field for free-text annotation on a payment.
**Files to touch:**
- `app/advance_payments/models/advance_payment.py` — add `notes: String(500), nullable`
- `app/advance_payments/schemas/advance_payment.py` — add `notes: Optional[str]` to create/update/response schemas
- `alembic/versions/` — add migration
**Acceptance criteria:** `POST` and `PATCH` advance-payment endpoints accept and persist `notes`; `GET` returns `notes`.

---

## [P3] 3.11 — סינון סטטוס ב-list (Status Filter on List Endpoint)
**Status:** PARTIAL
**Gap:** `GET /advance-payments` (per-client list) does not support `?status=` filter; only the overview endpoint filters by status.
**Files to touch:**
- `app/advance_payments/api/advance_payments.py` — add `status` query param
- `app/advance_payments/repositories/advance_payment_repository.py` — add optional status filter to `list_by_client()`
**Acceptance criteria:** `GET /advance-payments?client_id=&year=&status=overdue` returns only payments matching that status.

---

## [P3] 3.13 — שליחת תזכורת — Bulk (Bulk Reminder Send)
**Status:** PARTIAL
**Gap:** Reminder can be created individually via the reminders domain; no bulk send for all overdue advance payments exists.
**Files to touch:**
- `app/advance_payments/api/advance_payments_overview.py` — add `POST /advance-payments/reminders/bulk` accepting list of `payment_id`s
- `app/advance_payments/services/advance_payment_service.py` — add `bulk_send_reminders(payment_ids, actor)` calling notification service per client
**Acceptance criteria:** Bulk endpoint accepts `{"payment_ids": [...]}` and dispatches a reminder notification for each overdue payment; returns count of sent/failed.
