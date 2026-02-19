# Backend Capability Specification  
Binder & Billing CRM

## 1. System Overview
- **Architecture:** FastAPI app with strict layering `API → Service → Repository → ORM` and no raw SQL. ORM models use SQLAlchemy; schema auto-creates in `APP_ENV=development/test` via `Base.metadata.create_all()`. Production expects managed migrations. File-size rule: Python files targeted to ≤150 lines (some legacy files exceed).
- **Routing:** Business APIs mounted at `/api/v1/*`. Public endpoints: `GET /` (service probe), `GET /info`, `GET /health`. All other routes require JWT auth.
- **Auth model:** Bearer JWT (also set as HttpOnly cookie on login). Roles: `advisor` (super role) and `secretary`. Role enforcement via `require_role` dependency; inactive users or token-version mismatch → 401. Most business routes allow both roles; user/admin routes are advisor-only.
- **Error handling:** Central `app/core/exceptions.py` wraps HTTPException/validation/DB errors into `{"detail": ..., "error": {type,status_code,detail}}`. Routers raise HTTPException with plain strings; 422 handled by FastAPI.
- **Pagination conventions:** Query params `page` (default 1, ge 1) and `page_size` (defaults vary: 20 most routes, 50 for timeline/annual-report season). Many list endpoints slice in service/repo; some (tax-deadlines list without client filter) paginate in router after fetching all.
- **Enum handling:** Business enums are `str` subclasses defined beside models. Routers manually coerce/validate (e.g., `DeadlineType`, `VatType`, `CorrespondenceType`); invalid values return 400 with the raw message.
- **Derived state (never persisted):** SLA state, work_state, and operational signals are computed in services (SLAService, WorkStateService, SignalsService). Binder overdue/approaching and attention items are runtime derivations only.
- **Notifications:** Stored in `notifications` table; send flow uses stub WhatsApp/Email channels. Triggered by binder intake and SLA job; no public API.
- **Storage:** Permanent documents saved through `LocalStorageProvider` (local filesystem path key stored in DB). No S3 integration in code.
- **Time handling:** `utils.time.utcnow()` returns naive UTC datetime; all timestamps persisted naive UTC.

## 2. Domain: Clients
### Implemented Endpoints
- `POST /api/v1/clients` (advisor|secretary) — create client; 409 if `id_number` already exists.
- `GET /api/v1/clients` — filters: `status`, `has_signals`; paginated.
- `GET /api/v1/clients/{client_id}` — 404 if missing.
- `PATCH /api/v1/clients/{client_id}` — advisor required to set status `frozen/closed`; sets `closed_at` to today if closing without date.
- `GET /api/v1/clients/{client_id}/binders` — paginated list of binders with SLA/work_state enrichment; 404 if client missing.
- Excel helpers: `GET /api/v1/clients/export`, `GET /api/v1/clients/template`, `POST /api/v1/clients/import` (advisor-only; openpyxl required).
### Service Layer
- Validates unique `id_number` on create.
- `update_client` enforces advisor for freeze/close; fills `closed_at` default.
- `list_clients` optional `has_signals` filter computed via SignalsService over binders, documents, unpaid charges.
### Repository Capabilities
- CRUD + list/count with optional status; simple offset pagination.
### ORM Model
- `Client`: unique `id_number`, optional unique `primary_binder_number`; enums `ClientType`, `ClientStatus`.
### Known Gaps
- No delete endpoint. Import does per-row error collection; no dry-run. Signals-based filtering loads up to 1000 clients in memory.

## 3. Domain: Binders
### Implemented Endpoints
- `POST /api/v1/binders/receive` — create binder; prevents duplicate active `binder_number`; sets expected_return_at = received_at +90d; logs status history; sends notification.
- `POST /api/v1/binders/{id}/ready` — allowed from `in_office|overdue`; else 400.
- `POST /api/v1/binders/{id}/return` — requires `pickup_person_name` (defaults to current user name); allowed from `ready_for_pickup|overdue`; stamps `returned_at` today.
- `GET /api/v1/binders` — filters `status`, `client_id`, `work_state`, `sla_state`; derives `days_in_office`, `work_state`, `sla_state`, `signals`, `available_actions`.
- `GET /api/v1/binders/{id}` — single binder with derived fields; 404 if missing.
- Operations lists (paginated): `GET /api/v1/binders/open`, `/overdue`, `/due-today`.
- History: `GET /api/v1/binders/{id}/history` — 404 if binder missing.
### Service Layer
- BinderService handles transitions, validates readiness/return; writes status logs; triggers notifications.
- BinderOperationsService provides SLA-enriched lists; uses SLAService, WorkStateService, SignalsService.
- DailySLAJobService (no endpoint) scans active binders, sends approaching/overdue/ready notifications with idempotency checks per trigger.
### Repository Capabilities
- BinderRepository CRUD, list_active with filters, status updates, count by status; BinderStatusLog append/list; extensions for open/overdue/due-today/client lists with pagination.
### ORM Model
- `Binder` with enum `BinderStatus`; active-unique `binder_number` enforced via partial index; multiple date indexes.
- `BinderStatusLog` append-only audit trail.
### Known Gaps
- No binder deletion. Overdue flag stored? No—derived only. WorkState uses recent notifications heuristic; may query notifications per binder on each call.

## 4. Domain: Charges
### Implemented Endpoints
- `POST /api/v1/charges` (advisor) — create draft; amount must be >0; 400 on invalid client/amount.
- `POST /api/v1/charges/{id}/issue` (advisor) — only from draft.
- `POST /api/v1/charges/{id}/mark-paid` (advisor) — only from issued.
- `POST /api/v1/charges/{id}/cancel` (advisor) — cannot cancel paid or already canceled.
- `GET /api/v1/charges` (advisor|secretary) — filters `client_id`, `status`; paginated; secretary response omits amount/currency.
- `GET /api/v1/charges/{id}` — 404 if missing; secretary sees redacted fields.
### Service Layer
- Validates client existence and status transitions; sets timestamps on issue/paid.
### Repository Capabilities
- Create, get, list (order by created_at desc), count, update_status with optional extra fields.
### ORM Model
- `Charge` with enums `ChargeType`, `ChargeStatus`; monetary fields Numeric(10,2); timestamps for issue/paid.
### Known Gaps
- No invoice issuance; charges can exist without downstream invoice. No soft-delete.

## 5. Domain: Tax Deadlines
### Implemented Endpoints
- `POST /api/v1/tax-deadlines` — create pending deadline; validates `DeadlineType`; 400 if client missing.
- `GET /api/v1/tax-deadlines` — filters `client_id`, `deadline_type`, `status`; if no `client_id` provided, returns all pending due up to year 2099 then paginates in-memory.
- `GET /api/v1/tax-deadlines/{id}` — 404 if missing.
- `POST /api/v1/tax-deadlines/{id}/complete` — idempotent; 400 if not found.
- `GET /api/v1/tax-deadlines/dashboard/urgent` — returns `urgent` (overdue/red/yellow) and `upcoming` lists with client names.
### Service Layer
- Validates client existence on create; computes urgency (overdue/red ≤2 days, yellow ≤7, else green).
### Repository Capabilities
- Create, get, update_status, list_pending_due_by_date, list_overdue, list_by_client with optional status/type.
### ORM Model
- `TaxDeadline` with enums `DeadlineType`; status string (pending/completed); indexes on status, type, due_date.
### Known Gaps
- No edit/delete. Non-pending deadlines still returned when listing by client if status filter omitted.

## 6. Domain: Annual Reports
### Implemented Endpoints
- Create/read:
  - `POST /api/v1/annual-reports` — creates report, auto-selects `form_type` via `client_type` → `FORM_MAP`, sets deadline (standard/extended/custom), generates schedules, seeds status history.
  - `GET /api/v1/annual-reports` — list with optional `tax_year`, paginated (default 20, max 200).
  - `GET /api/v1/annual-reports/{id}` — returns schedules + status history; 404 if missing.
  - `GET /api/v1/annual-reports/kanban/view` — stage-grouped view.
  - `GET /api/v1/annual-reports/overdue` — filing_deadline passed & open statuses.
- Status/deadline:
  - `POST /api/v1/annual-reports/{id}/status` — validated against `VALID_TRANSITIONS`; populates status history; accepts optional ITA refs and amounts.
  - `POST /api/v1/annual-reports/{id}/submit` — convenience to `submitted`.
  - `POST /api/v1/annual-reports/{id}/deadline` — recomputes deadline per `DeadlineType`, logs history.
  - `POST /api/v1/annual-reports/{id}/transition` — stage shortcut mapping; auto-inserts COLLECTING_DOCS step when jumping from NOT_STARTED.
  - `GET /api/v1/annual-reports/{id}/history` — status history list (404 if report missing).
- Schedules:
  - `GET /api/v1/annual-reports/{id}/schedules`
  - `POST /api/v1/annual-reports/{id}/schedules` — add schedule; validates enum.
  - `POST /api/v1/annual-reports/{id}/schedules/complete` — marks required schedule complete or 400 if absent.
- Detail companion table:
  - `GET /api/v1/annual-reports/{id}/details` — returns all-null payload if detail row absent; 404 if report missing.
  - `PATCH /api/v1/annual-reports/{id}/details` — upsert tax_refund_amount/tax_due_amount/client_approved_at/internal_notes; 404 if report missing.
- Client & season views:
  - `GET /api/v1/clients/{id}/annual-reports`
  - `GET /api/v1/tax-year/{tax_year}/reports` (paginated 50 default)
  - `GET /api/v1/tax-year/{tax_year}/summary` — counts per status, completion %, overdue count.
### Service Layer
- Create validates client and uniqueness per (client,tax_year); derives deadlines; auto-adds schedules based on income flags; appends status history.
- Transition enforces `VALID_TRANSITIONS`, sets submitted/assessment/refund fields when relevant, logs history.
- Deadline update recalculates dates; schedule service manages required/complete flags.
- Query service provides kanban grouping into `ReportStage`.
### Repository Capabilities
- AnnualReportRepository composes report/schedule/status-history mixins: create/get/list/count by status/tax_year, list_overdue, list_all_with_clients (for kanban), append_status_history, schedule add/complete/check completion, detail upsert/read.
### ORM Models
- `AnnualReport` with enums `AnnualReportStatus`, `ClientTypeForReport`, `AnnualReportForm`, `DeadlineType`; unique index on (client_id, tax_year); status & deadline indexes.
- `AnnualReportDetail` 1:1 with report (unique report_id).
- `AnnualReportScheduleEntry` with `AnnualReportSchedule` enum and completion flags.
- `AnnualReportStatusHistory` append-only audit log.
### Known Gaps
- No delete; no reassignment validation for `assigned_to`; kanban `days_until_due` uses created_at vs filing_deadline (not remaining days).

## 7. Domain: Dashboard
### Implemented Endpoints
- `GET /api/v1/dashboard/summary` (any authenticated user) — counts binders by status + attention items (idle/ready/unpaid for advisor).
- `GET /api/v1/dashboard/overview` (advisor) — totals + quick_actions + attention.
- `GET /api/v1/dashboard/work-queue` — paginated operational queue with work_state/signals.
- `GET /api/v1/dashboard/alerts` — overdue/near-SLA alerts.
- `GET /api/v1/dashboard/attention` — attention items; unpaid charges only for advisor.
- `GET /api/v1/dashboard/tax-submissions` — tax-year widget built from annual report statuses.
### Services/Logic
- DashboardService aggregates counts and delegates to DashboardExtendedService.
- DashboardExtendedService builds work_queue/alerts/attention using SLAService, WorkStateService, SignalsService and unpaid charges (advisor only).
- DashboardOverviewService computes metrics via DashboardOverviewRepository and assembles quick actions (ready/return binder, mark charge paid, freeze/activate client).
- DashboardTaxService aggregates submission stats + delegates deadline summary (reuse TaxDeadlineService).
### Known Gaps
- No caching; overview quick actions pick first matching entities (heuristic). Attention lists load all active binders in memory.

## 8. Domain: Notifications (internal)
- **Endpoints:** None.
- **Service:** NotificationService sends via WhatsAppChannel then email fallback; persists every attempt; idempotency for SLA job via NotificationRepository `exists_for_binder_trigger`.
- **Models/Enums:** NotificationChannel (`whatsapp|email`), NotificationStatus (`pending|sent|failed`), NotificationTrigger (binder events, manual payment reminder).
- **Repository:** create/mark_sent/mark_failed, list_by_client (pagination), check existing trigger.
- **Gaps:** WhatsApp/Email channels are stubs; no delivery webhook; no resend UI.

## 9. Domain: Authority Contacts
### Implemented Endpoints
- `POST /api/v1/clients/{id}/authority-contacts` (advisor|secretary) — create contact; validates `ContactType`.
- `GET /api/v1/clients/{id}/authority-contacts` — optional `contact_type` filter.
- `PATCH /api/v1/authority-contacts/{contact_id}` — updates; validates contact_type when provided; 400 if not found.
- `DELETE /api/v1/authority-contacts/{contact_id}` — advisor-only; 404 if missing.
### Service/Repo/Model
- Validates client existence on create; otherwise straightforward CRUD. Model indexed by client_id/contact_type; enum `ContactType`.
### Gaps
- No pagination on list; no cross-tenant checks beyond client existence.

## 10. Domain: Advance Payments
### Implemented Endpoints
- `GET /api/v1/advance-payments` — requires `client_id` and `year` (defaults to current UTC year); paginated slice of in-memory list; 404 if client missing.
- `PATCH /api/v1/advance-payments/{payment_id}` — updates `paid_amount`/`status`; validates enum; 404 if missing.
### Service/Repo/Model
- Repository: list_by_client_year ordered by month asc; get/update/create; unique (client,year,month); status index.
- Service validates status values; no creation exposed via API.
### Gaps
- No API to create rows; assumes external seeding. Pagination done after fetching all rows.

## 11. Domain: Client Tax Profile
### Implemented Endpoints
- `GET /api/v1/clients/{id}/tax-profile` — returns empty payload (fields None) if row absent; 404 if client missing.
- `PATCH /api/v1/clients/{id}/tax-profile` — validates `vat_type` enum; 404 if client missing.
### Service/Repo/Model
- Upsert profile; sets `updated_at` on updates. Enum `VatType` (monthly/bimonthly/exempt); one-to-one via unique client_id.
### Gaps
- No creation timestamp in response when row absent (by design). No delete.

## 12. Domain: Correspondence
### Implemented Endpoints
- `GET /api/v1/clients/{id}/correspondence` — list entries ordered by occurred_at desc.
- `POST /api/v1/clients/{id}/correspondence` — creates entry; validates `correspondence_type`; 404 if client missing; 400 if contact_id not linked to client.
### Service/Repo/Model
- Model includes optional contact_id (FK authority_contacts), created_by current user, occurred_at required; indexes on client_id and occurred_at.
### Gaps
- No pagination; no update/delete.

## 13. Domain: Permanent Documents
### Implemented Endpoints
- `POST /api/v1/documents/upload` — multipart upload; validates `DocumentType`; stores via LocalStorageProvider; 400 on missing client or import errors.
- `GET /api/v1/documents/client/{id}` — list documents for client.
- `GET /api/v1/documents/client/{id}/signals` — returns operational signals (missing docs + binder SLA summaries).
### Service/Repo/Model
- DocumentType enum (`id_copy`, `power_of_attorney`, `engagement_agreement`); `is_present` flag always True on upload. SignalsService uses PermanentDocumentService `get_missing_document_types`.
### Gaps
- No delete/replace; storage provider is local only; upload reads entire file into memory.

## 14. Domain: Reminders
### Implemented Endpoints
- `GET /api/v1/reminders` — filters optional `status` (pending/sent/canceled), paginated.
- `GET /api/v1/reminders/{id}` — 404 if missing.
- `POST /api/v1/reminders` — creates reminder; type-specific required FK checks: `tax_deadline_id` for tax_deadline_approaching, `binder_id` for binder_idle, `charge_id` for unpaid_charge, custom requires message. Validates `days_before` ≥0 and client existence; type regex enforced by schema.
- `POST /api/v1/reminders/{id}/cancel` — only pending; 400 otherwise.
- `POST /api/v1/reminders/{id}/mark-sent` — only pending; stamps sent_at.
### Service/Repo/Model
- ReminderType enum, ReminderStatus enum; repo provides list/count by status and pending-by-date. Service delegates to factory/status modules with validation.
### Gaps
- No scheduled job wired to send_on; reminders are stored but not dispatched. Pagination sometimes after DB query limited to 20 default.

## 15. Domain: Timeline
### Implemented Endpoint
- `GET /api/v1/clients/{id}/timeline` — paginated (page_size default 50, max 200) aggregated events.
### Service/Logic
- Aggregates binder events (receive/return/status changes), notifications, charges (created/issued/paid), and attached invoice if present; sorts by timestamp desc.
- Uses `actions` contracts to attach available_actions.
### Repositories/Models
- No dedicated timeline table; pulls from Binder, BinderStatusLog, Notification, Charge, Invoice. TimelineRepository only lists binders by client.
### Gaps
- No events for tax deadlines/annual reports; pagination done after loading all events into memory.

## 16. Domain: Search
### Implemented Endpoint
- `GET /api/v1/search` — filters: general `query`, `client_name`, `id_number`, `binder_number`, `work_state`, `sla_state`, `signal_type[]`, `has_signals`; paginated.
### Service/Logic
- Client search scans up to 1000 clients in memory; binder search iterates active binders, derives work_state/sla_state/signals per binder, applies filters, returns mixed result objects.
### Gaps
- No full-text/indexed search; bounded in-memory scans; no pagination at DB level.

## 17. Domain: Users & Authentication
### Auth Endpoints
- `POST /api/v1/auth/login` — bcrypt verify; sets JWT cookie; doubles TTL if `rememberMe=true`; 401 on invalid creds; 401 inactive user.
- `POST /api/v1/auth/logout` — clears cookie (token remains valid until expiry).
### User Management Endpoints (advisor-only)
- `POST /api/v1/users` — create; validates password length ≥8; 409 if email exists.
- `GET /api/v1/users` — paginated list.
- `GET /api/v1/users/{id}` — 404 if missing.
- `PATCH /api/v1/users/{id}` — mutable: full_name, phone, role; immutable fields rejected with 400.
- `POST /api/v1/users/{id}/activate` — reactivate.
- `POST /api/v1/users/{id}/deactivate` — cannot deactivate self; bumps token_version.
- `POST /api/v1/users/{id}/reset-password` — validates password length; bumps token_version.
- Audit logs: `GET /api/v1/users/audit-logs` with filters (action/target/actor/email/date range), paginated; advisor-only.
### Services/Repos/Models
- `UserRole` enum; `User` model with token_version + last_login_at. AuthService handles JWT encode/decode with exp, tv match. Audit logs stored in `user_audit_logs` with enums `AuditAction`, `AuditStatus`.
### Known Gaps
- No password change for self; no MFA; logout does not invalidate token server-side.

## 18. Domain: Signature Requests (Digital Signing)
### Implemented Endpoints
- Advisor/secretary:
  - `POST /api/v1/signature-requests` — create draft; validates request_type enum; links optional annual_report_id/document_id.
  - `GET /api/v1/signature-requests/pending` — paginated pending_signature list.
  - `GET /api/v1/signature-requests/{id}` — returns request + audit trail; 404 if missing.
  - `POST /api/v1/signature-requests/{id}/send` — sets signing token, expiry, status pending_signature; returns token once.
  - `POST /api/v1/signature-requests/{id}/cancel` — sets status canceled; requires reason optional.
  - `GET /api/v1/signature-requests/{id}/audit-trail`
- Client-scoped:
  - `GET /api/v1/clients/{id}/signature-requests` — optional status filter; paginated.
- Public signer (no JWT):
  - `GET /sign/{token}` — records view; returns signer-facing summary or 400 on invalid/expired.
  - `POST /sign/{token}/approve` — marks signed, records audit.
  - `POST /sign/{token}/decline` — marks declined with reason.
### Service/Repo/Model
- Model `SignatureRequest` with enums `SignatureRequestStatus`, `SignatureRequestType`; audit events table append-only. Repository supports create/update, list by client/status, list pending, get by token, expire_overdue (not scheduled). Service modules handle token generation, expiry days, audit logging, signer IP/user-agent capture.
### Gaps
- No job wired to expire overdue requests automatically. Storage_key/content_hash optional; no actual document upload in flow.

## 19. Domain: Reports (Aging)
### Implemented Endpoints
- `GET /api/v1/reports/aging` (advisor) — returns computed aging buckets for issued-but-unpaid charges as of `as_of_date` (default today).
- `GET /api/v1/reports/aging/export?format=excel|pdf` — generates temp file via openpyxl/reportlab; returns download; 500 if library missing.
### Service/Logic
- AgingReportService groups unpaid charges per client into 0-30/31-60/61-90/90+; computes totals and oldest invoice age.
- ExportService writes to temp `exports/` dir; returns filepath/filename.
### Gaps
- No CSV; no streaming; memory aggregation over all issued charges (page_size 10000).

## 20. Domain: Advance / Misc Infrastructure
- **Notifications job & SLA job:** Present as services only; no scheduler wiring.
- **Invoice:** ORM + repository for charge-linked invoice references; no API/services creating invoices (only read in timeline).
- **Actions:** Pure metadata for UI available_actions (binders/charges/clients); no API.
- **Middleware:** RequestIDMiddleware adds `X-Request-ID` if missing.
- **Health/Info Root:** `GET /health` verifies DB connectivity; `GET /info` returns app/env; `GET /` returns static service status.

## 21. Known Cross-Cutting Gaps
- Many list endpoints paginate in memory after full fetch (clients has_signals, tax-deadlines global list, timeline aggregation, search, dashboard attention/work-queue).
- No rate limiting or throttling.
- No background workers configured for reminders, signature expiry, or SLA job; these must be triggered externally.
- Storage/notification providers are local stubs—no cloud integration present in code.
