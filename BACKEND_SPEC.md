# Backend Capability Specification

> Routes are authoritative in `API_CONTRACT.md`. This file documents current implementation behavior (services/repos/models) and known debt, based on the code under `app/`.

---

## System-Wide Notes

- **Error envelope:** central handlers in `app/core/exceptions.py` normalize `HTTPException`, validation, DB, and unexpected errors.
- **Time handling:** `app/utils/time_utils.py::utcnow()` returns naive UTC datetimes.
- **Derived state:** `work_state` and operational signals are computed (`WorkStateService`, `SignalsService`), never persisted.
- **Storage provider factory:** `LocalStorageProvider` in dev/test; `S3StorageProvider` in non-dev/test with required `R2_*` env vars.
- **Background jobs:** `app/lifespan.py` starts startup signature-expiry + daily signature-expiry + daily reminder jobs.

---

## 1. Health

- **Service/Repo:** deterministic DB connectivity probe (`query(1).first()`), no writes.
- **API:** `GET /health` returns 200 healthy, 503 unhealthy.

## 2. Clients

- **Service:** create enforces unique `id_number`; `update_client` restricts `frozen/closed` to advisor and auto-fills `closed_at` for close.
- **Signals filter:** `list_clients(..., has_signals=...)` computes signals in memory, hard-capped by `_HAS_SIGNALS_FETCH_LIMIT = 1000`; exceeding cap raises `CLIENT.SIGNAL_FILTER_LIMIT`.
- **Repo/ORM:** standard CRUD/list/count with pagination; unique `id_number`, optional unique `primary_binder_number`.
- **Known gap:** Excel import is partial-success oriented (row-level errors), not all-or-nothing transaction.

## 3. Binders

- **Service:** intake/create-or-reuse flow, ready/return transitions, status logs, notification triggers.
- **Derived state:** operations/list views enrich with `work_state` and signals.
- **Known gap:** notification activity check in work-state derives by fetching client notifications (`page_size=100`) then filtering by binder in memory (no binder-scoped notification query).

## 4. Charges

- **Service:** lifecycle `draft -> issued -> paid/canceled`; deletion allowed only for draft charges; issuing auto-creates unpaid-charge reminder.
- **Repo:** list/count with filters and pagination; SQL aging aggregation via `get_aging_buckets`; soft-delete supported.
- **API surface implemented:** includes bulk action and `DELETE /charges/{id}` soft-delete.
- **Known gap:** no invoice issuance workflow from charge lifecycle (invoice domain is read-side for timeline).

## 5. Tax Deadlines

- **Service:** create validates client and auto-creates reminder (`days_before=7`); urgency logic: overdue/red/yellow/green.
- **List behavior:** global list (`GET /tax-deadlines` without `client_id`/`client_name`) pulls pending deadlines and truncates to `_GLOBAL_DEADLINE_FETCH_LIMIT = 500` before page slicing.
- **Known gap:** global listing still performs in-memory pagination after bounded prefetch instead of true DB pagination.

## 6. Annual Reports

- **Service set:** create/read, status transitions, kanban grouping, schedule management, deadline management, detail/financial CRUD, annex, tax engine, PDF export.
- **Core rules:** uniqueness per `(client_id, tax_year)`, transition validation, status history append, derived deadlines/schedules.
- **ORM:** report, detail, schedule entries, status history, income lines, expense lines, annex data.

## 7. Dashboard

- **Service:** summary, overview, work queue, attention, tax submissions.
- **Limits:** `_ACTIVE_BINDERS_FETCH_LIMIT = 1000`, `_UNPAID_CHARGES_FETCH_LIMIT = 500` in extended service.
- **Current behavior:** items beyond limits are silently excluded — binders/charges beyond ceiling are not surfaced in dashboard without error. No `AppError` is raised.

## 8. Notifications

- **Service:** sends WhatsApp first when configured, otherwise email fallback; persists notification records and status (`pending/sent/failed`).
- **Infra:** real SendGrid + 360dialog adapters exist; behavior is config-gated (`NOTIFICATIONS_ENABLED`, API keys).
- **Known gaps:** no webhook reconciliation, no retry scheduler, no dedicated idempotency guard in repository/service.

## 9. Authority Contacts

- **Service:** validates client existence on create; standard CRUD otherwise.
- **ORM:** enum-based contact type, indexed by client/contact type.

## 10. Advance Payments

- **Service:** create/update/list/overview/KPIs/chart/suggestion; uniqueness per `(client, year, month)` enforced.
- **ORM:** status is enforced with enum type (`pg_enum(AdvancePaymentStatus)`), not free-form string.

## 11. Client Tax Profile

- **Service:** upsert semantics; update sets `updated_at`.
- **Known behavior:** empty shell response when no profile exists for an existing client.
- **Known gap:** no delete endpoint.

## 12. Correspondence

- **Service:** validates `contact_id` belongs to client on create/update.
- **ORM:** soft-delete model (`deleted_at`) with client/time indexing.
- **Known gap:** no hard-delete path.

## 13. Permanent Documents

- **Service:** upload, replace, list, delete, missing-required-docs computation.
- **Upload behavior:** service reads file fully into memory (`file_data.read()`) for size/mime validation before upload.
- **Storage:** local provider writes files to `./storage`; S3 provider uses `upload_fileobj`.
- **Known gap:** in-memory buffering exists regardless of provider due to service-level read.

## 14. Reminders

- **Service:** type-specific FK validation and transitions (`pending -> sent|canceled`).
- **Jobs:** daily background job dispatches pending reminders by marking them sent.
- **Known gap:** reminder dispatch job currently marks sent only; it does not invoke notification channels.

## 15. Timeline

- **Aggregation sources:** binders + status logs, notifications, charges, invoices, tax deadlines, annual reports, reminders, signature requests, client/profile/document events.
- **Pagination model:** aggregate in memory, sort desc by timestamp, then page slice.
- **Limits:** per-entity `_TIMELINE_BULK_LIMIT = 500` safety ceilings.

## 16. Search

- **DB-paginated path:** pure client search (`query/client_name/id_number`, no binder-derived filters) uses repo-level pagination.
- **In-memory path:** mixed/binder/derived filters (`work_state`, `signal_type`, `has_signals`) fetch bounded sets then paginate in memory.
- **Limits:** `_MIXED_SEARCH_BINDER_LIMIT = 1000`, `_MIXED_SEARCH_CLIENT_LIMIT = 500`.

## 17. Users & Authentication

- **Auth:** bcrypt, JWT with `tv` (`token_version`) claim, remember-me doubles TTL, cookie + bearer accepted.
- **Invalidation:** logout/deactivate/reset-password bump `token_version`.
- **Audit:** login/logout and user-management actions persisted to `user_audit_logs`.
- **Known gaps:** no MFA; no self-service password change endpoint.

## 18. Signature Requests

- **Service:** request create/send/cancel, signer approve/decline/view, audit trail recording.
- **Expiry:** startup run + daily background expiry job active via lifespan.
- **Known gap:** no integrated document upload/signature artifact workflow beyond request metadata and hash fields.

## 19. Reports (Aging)

- **Service:** SQL-based bucket aggregation from issued unpaid charges (`current/30/60/90+`), client enrichment, summary totals.
- **Export:** Excel/PDF exporters write temp files under OS temp `exports/`.
- **Known gaps:** no CSV; exports are file-based (not streaming responses).

## 20. VAT Reports

- **Lifecycle:** `pending_materials -> material_received -> data_entry_in_progress -> ready_for_review -> filed`, with advisor-only send-back/file operations.
- **Constraints:** one work item per `(client_id, period)` enforced both in service checks and DB `UniqueConstraint`.
- **Locking:** filed items block invoice mutations and period re-filing checks.

## 21. Infrastructure & Misc

- **Invoice domain:** repository/model used as timeline enrichment source (no dedicated invoice creation API).
- **Actions domain:** metadata contracts for `available_actions` across entities.
- **Middleware:** `RequestIDMiddleware` sets/preserves `X-Request-ID`.

---

## Cross-Cutting Gaps

- Several endpoints still do in-memory aggregation/pagination after bounded prefetch (dashboard/search/timeline/tax-deadline global list).
- No rate limiting/throttling middleware.
- Reminder and notification background processing is minimal (no retries, no delivery reconciliation).