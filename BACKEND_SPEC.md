# Backend Capability Specification

> Routes are authoritative in `API_CONTRACT.md`. This document covers implementation details: service logic, repo capabilities, ORM models, and known gaps per domain.

---

## System-Wide Notes

- **Error handling:** `app/core/exceptions.py` wraps HTTPException/validation/DB errors into standard envelope. Routers raise `HTTPException` with plain strings.
- **Pagination:** Most list endpoints paginate via offset in repo. Exceptions: clients `has_signals` filter, tax-deadlines global list, timeline aggregation, and search all paginate in memory after full fetch.
- **Enum handling:** Business enums are `str` subclasses defined beside models. Invalid values return 400.
- **Timestamps:** `utils.time.utcnow()` — naive UTC everywhere.
- **Derived state:** `work_state` and signals are computed in `WorkStateService`/`SignalsService`, never persisted.
- **Storage:** `LocalStorageProvider` — local filesystem only, no S3.
- **Notifications:** Triggered by binder intake; WhatsApp/Email channels are stubs.

---

## 1. Clients

**Service:** Validates unique `id_number` on create. `update_client` enforces advisor for `frozen`/`closed`; fills `closed_at` default. `list_clients` optional `has_signals` filter runs `SignalsService` over binders, documents, and unpaid charges.

**Repo:** CRUD + list/count with optional status; simple offset pagination.

**ORM:** `Client` — unique `id_number`, optional unique `primary_binder_number`; enums `ClientType`, `ClientStatus`.

**Gaps:** No delete. Import does per-row error collection; no dry-run. `has_signals` filter loads up to 1000 clients in memory.

---

## 2. Binders

**Service:** `BinderService` handles transitions, validates readiness/return, writes status logs, triggers notifications. `BinderOperationsService` provides work_state-enriched lists via `WorkStateService` and `SignalsService`.

**Repo:** `BinderRepository` — CRUD, list_active with filters, status updates, count by status. `BinderStatusLog` — append/list. Extensions for open/overdue/due-today/client lists with pagination.

**ORM:** `Binder` — `BinderStatus` enum; active-unique `binder_number` via partial index; multiple date indexes. `BinderStatusLog` — append-only.

**Gaps:** No deletion. WorkState uses recent-notifications heuristic; may query notifications per binder on each call.

---

## 3. Charges

**Service:** Validates client existence and status transitions; sets `issued_at`/`paid_at` timestamps.

**Repo:** Create, get, list (order by `created_at` desc), count, `update_status` with optional extra fields.

**ORM:** `Charge` — `ChargeType`, `ChargeStatus` enums; monetary fields `Numeric(10,2)`; issue/paid timestamps.

**Gaps:** No invoice issuance from charges. No soft-delete.

---

## 4. Tax Deadlines

**Service:** Validates client on create. Computes urgency: overdue = red, ≤2 days = red, ≤7 days = yellow, else green.

**Repo:** Create, get, `update_status`, `list_pending_due_by_date`, `list_overdue`, `list_by_client` with optional status/type filter.

**ORM:** `TaxDeadline` — `DeadlineType` enum; status string; indexes on status, type, `due_date`.

**Gaps:** No edit/delete. Without `client_id` filter, all pending deadlines are fetched then paginated in memory.

---

## 5. Annual Reports

**Service:** Create validates client and uniqueness per (client, tax_year); derives deadlines; auto-adds schedules from income flags; seeds status history. Transition enforces `VALID_TRANSITIONS`, sets submitted/assessment/refund fields, logs history. Deadline update recalculates dates. Query service groups into `ReportStage` for kanban.

**Repo:** `AnnualReportRepository` — create/get/list/count by status/tax_year, `list_overdue`, `list_all_with_clients` (kanban), `append_status_history`, schedule add/complete/check, detail upsert/read.

**ORM:** `AnnualReport` — enums `AnnualReportStatus`, `ClientTypeForReport`, `AnnualReportForm`, `DeadlineType`; unique index on (client_id, tax_year). `AnnualReportDetail` — 1:1 with report. `AnnualReportScheduleEntry` — `AnnualReportSchedule` enum + completion flags. `AnnualReportStatusHistory` — append-only.

**Gaps:** No delete. No `assigned_to` validation. Kanban `days_until_due` incorrectly uses `created_at` vs `filing_deadline`.

---

## 6. Dashboard

**Service:** `DashboardService` aggregates counts; delegates to `DashboardExtendedService`. `DashboardExtendedService` builds work_queue/alerts/attention via `WorkStateService`, `SignalsService`, unpaid charges (advisor only). `DashboardOverviewService` assembles quick actions (ready/return binder, mark charge paid, freeze/activate client). `DashboardTaxService` aggregates submission stats.

**Gaps:** No caching. Quick actions pick first matching entity (heuristic). Attention lists load all active binders in memory.

---

## 7. Notifications (internal — no API)

**Service:** `NotificationService` — sends via `WhatsAppChannel` then email fallback; persists every attempt; idempotency via `exists_for_binder_trigger`.

**ORM:** `Notification` — enums `NotificationChannel` (`whatsapp|email`), `NotificationStatus` (`pending|sent|failed`), `NotificationTrigger`.

**Repo:** create, `mark_sent`, `mark_failed`, `list_by_client`, `check_existing_trigger`.

**Gaps:** Channels are stubs. No delivery webhook. No resend UI. No scheduler wired.

---

## 8. Authority Contacts

**Service:** Validates client existence on create; otherwise CRUD.

**ORM:** `AuthorityContact` — indexed by `client_id`/`contact_type`; `ContactType` enum.

**Gaps:** No pagination on list endpoint.

---

## 9. Advance Payments

**Service:** Validates status enum values. No creation exposed via API — rows assumed externally seeded.

**Repo:** `list_by_client_year` ordered by month asc; get/update/create; unique (client, year, month); status index.

**ORM:** `AdvancePayment` — status as string (no enum enforcement at ORM level).

**Gaps:** No create API. Pagination done after fetching all rows in memory.

---

## 10. Client Tax Profile

**Service:** Upsert; sets `updated_at` on update.

**ORM:** `ClientTaxProfile` — `VatType` enum (`monthly`, `bimonthly`, `exempt`); unique `client_id`.

**Gaps:** No delete. No creation timestamp in empty shell response (by design).

---

## 11. Correspondence

**Service:** Validates `contact_id` is linked to client before create.

**ORM:** `Correspondence` — optional `contact_id` FK to authority_contacts; `created_by` current user; `occurred_at` required; indexes on `client_id` and `occurred_at`.

**Gaps:** No pagination. No update/delete.

---

## 12. Permanent Documents

**Service:** `DocumentType` enum validated on upload. `SignalsService` calls `get_missing_document_types`.

**ORM:** `PermanentDocument` — `is_present` always True on upload; `storage_key` holds local path.

**Gaps:** No delete/replace. Storage is local filesystem only. Upload reads entire file into memory.

---

## 13. Reminders

**Service:** Type-specific FK validation (`tax_deadline_id`/`binder_id`/`charge_id`). Status transitions: pending → sent or canceled only.

**ORM:** `Reminder` — `ReminderType`, `ReminderStatus` enums; `send_on` date; `sent_at` timestamp.

**Repo:** list/count by status; `pending_by_date`.

**Gaps:** No scheduler wired to `send_on`. Reminders are stored but never auto-dispatched.

---

## 14. Timeline

**Service:** Aggregates binder events (receive/return/status changes), notifications, charges (created/issued/paid), invoice if present; sorts by timestamp desc. Attaches `available_actions` via `actions` contracts.

**Repo:** No dedicated table. Pulls from `Binder`, `BinderStatusLog`, `Notification`, `Charge`, `Invoice`.

**Gaps:** No events for tax deadlines or annual reports. Full aggregation happens in memory before pagination.

---

## 15. Search

**Service:** Client search scans up to 1000 clients in memory. Binder search iterates all active binders, derives work_state/signals per binder, applies filters.

**Gaps:** No full-text or indexed search. No DB-level pagination.

---

## 16. Users & Authentication

**Auth service:** bcrypt verify; JWT encode/decode with `exp` + `token_version` match; doubles TTL on `remember_me`.

**User service:** Password min 8 chars. Deactivation bumps `token_version` to invalidate active sessions. Audit events stored in `user_audit_logs`.

**ORM:** `User` — `UserRole` enum; `token_version`, `last_login_at`. `UserAuditLog` — `AuditAction`, `AuditStatus` enums.

**Gaps:** No self-service password change. No MFA. Logout does not server-side invalidate JWT.

---

## 17. Signature Requests

**Service:** Token generation, expiry (default 14 days), audit logging, signer IP/user-agent capture. `expire_overdue` method exists but is not scheduled.

**ORM:** `SignatureRequest` — `SignatureRequestStatus`, `SignatureRequestType` enums. `SignatureRequestAuditEvent` — append-only; field names `occurred_at` and `audit_trail`.

**Gaps:** No scheduled expiry job. No actual document upload in signing flow.

---

## 18. Reports (Aging)

**Service:** `AgingReportService` groups unpaid charges per client into 0-30/31-60/61-90/90+ day buckets. `ExportService` writes to temp `exports/` dir.

**Gaps:** No CSV format. No streaming. Aggregates over full issued charge set (page_size 10000).

---

## 19. VAT Reports

**Service:** Status machine: `pending_materials → material_received → data_entry_in_progress → ready_for_review → filed`. `send-back` moves back to `data_entry_in_progress`. Filing locks period. Invoices blocked after filing.

**ORM:** `VatWorkItem` — status enum; `VatInvoice` — `invoice_type` enum.

**Gaps:** No period uniqueness enforcement at DB level beyond service check.

---

## 20. Infrastructure & Misc

- **Invoice:** ORM + repo for charge-linked invoice references; no API/service creates invoices (read-only in timeline).
- **Actions:** Pure metadata for `available_actions` on binders/charges/clients; no API.
- **Middleware:** `RequestIDMiddleware` adds `X-Request-ID` if missing.
- **Background jobs:** No scheduler configured. Reminder dispatch and signature expiry must be triggered externally.

---

## Cross-Cutting Gaps

- Many list endpoints paginate in memory after full DB fetch.
- No rate limiting or throttling anywhere.
- No background workers configured for reminders, signature expiry, or notifications.
- Storage and notification providers are local stubs — no cloud integration.
