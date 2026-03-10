## [P3] 3.13 — שליחת תזכורת — Bulk (Bulk Reminder Send)
**Status:** PARTIAL
**Gap:** Reminder can be created individually via the reminders domain; no bulk send for all overdue advance payments exists.
**Files to touch:**
- `app/advance_payments/api/advance_payments_overview.py` — add `POST /advance-payments/reminders/bulk` accepting list of `payment_id`s
- `app/advance_payments/services/advance_payment_service.py` — add `bulk_send_reminders(payment_ids, actor)` calling notification service per client
**Acceptance criteria:** Bulk endpoint accepts `{"payment_ids": [...]}` and dispatches a reminder notification for each overdue payment; returns count of sent/failed.

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