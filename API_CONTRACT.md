# API Contract

## Conventions

- Base path: `/api/v1`. Public meta: `GET /`, `GET /info`, `GET /health`. Public signing: `/sign/*`.
- Auth: `POST /api/v1/auth/login` issues JWT; send as `Authorization: Bearer <token>` or via HttpOnly `access_token` cookie. `POST /api/v1/auth/logout` clears cookie and server-side invalidates token.
- Roles: `advisor` (elevated) and `secretary` (operational). `require_role` enforces where noted; otherwise any authenticated user may access.
- Content types: JSON unless stated; uploads use `multipart/form-data`; downloads return files with appropriate headers.
- Pagination: `page` (default 1) and `page_size` (default 20, max 100) unless noted. Exceptions: timeline/annual-report season default 50; VAT work-items default 50, max 200.
- Error envelope: `{ "detail": "...", "error": { "type": "...", "detail": "...", "status_code": N } }`.

---

## Service Metadata (no auth)

- `GET /` → `{ service, status }`
- `GET /info` → `{ app, env }`
- `GET /health` → 200 with DB result, 503 when unhealthy

---

## Authentication

- `POST /api/v1/auth/login` — body: `email`, `password`, `remember_me?`; returns `{ token, user { id, full_name, role } }`; sets HttpOnly cookie (`remember_me` doubles TTL).
- `POST /api/v1/auth/logout` — bumps `token_version` (invalidates all active tokens); clears auth cookie; 204.

---

## Users (advisor only)

- `POST /api/v1/users` — create (`full_name`, `email`, `role`, `password` ≥8 chars, `phone?`); 409 on duplicate email.
- `GET /api/v1/users` — paginated list.
- `GET /api/v1/users/{id}` — 404 if missing.
- `PATCH /api/v1/users/{id}` — mutable: `full_name`, `phone`, `role`; immutable fields rejected with 400.
- `POST /api/v1/users/{id}/activate`
- `POST /api/v1/users/{id}/deactivate` — cannot deactivate self; bumps `token_version`.
- `POST /api/v1/users/{id}/reset-password` — validates length; bumps `token_version`.
- `GET /api/v1/users/audit-logs` — filters: `action`, `target_user_id`, `actor_user_id`, `email`, `from`, `to`; paginated.

---

## Clients (advisor + secretary)

- `POST /api/v1/clients` — create (`full_name`, `id_number`, `client_type`, `opened_at`, `phone?`, `email?`); 409 on duplicate `id_number`.
- `GET /api/v1/clients` — filters: `status`, `has_signals`, `search`; paginated.
- `GET /api/v1/clients/{id}` — 404 if missing.
- `PATCH /api/v1/clients/{id}` — updatable: `full_name`, `phone`, `email`, `notes`, `status`, `client_type`, `primary_binder_number`, `address_street`, `address_building_number`, `address_apartment`, `address_city`, `address_zip_code`; advisor required for `frozen`/`closed`.
- `DELETE /api/v1/clients/{id}` (advisor) — soft-delete; 204.
- `GET /api/v1/clients/{id}/status-card` — summary card with signals and open items.

### Excel import/export

- `GET /api/v1/clients/export` — XLSX download.
- `GET /api/v1/clients/template` — XLSX template download.
- `POST /api/v1/clients/import` (advisor) — multipart XLSX; returns `{ created, total_rows, errors[] }`.

### Sub-resources

- `GET /api/v1/clients/{id}/tax-profile` — empty shell if none; 404 if client missing.
- `PATCH /api/v1/clients/{id}/tax-profile` — fields: `entity_type`, `vat_reporting_frequency`, `vat_exempt_ceiling`, `advance_rate`, `accountant_name`.
- `GET /api/v1/clients/{id}/binders` — paginated extended binder list; 404 if client missing.
- `GET /api/v1/clients/{id}/timeline` — paginated event feed (default page_size 50, max 200).
- `GET /api/v1/clients/{id}/correspondence` — paginated list ordered by `occurred_at` desc.
- `POST /api/v1/clients/{id}/correspondence` — body: `correspondence_type`, `subject`, `occurred_at`, `notes?`, `contact_id?`; 400 if `contact_id` not linked to client.
- `PATCH /api/v1/clients/{id}/correspondence/{correspondence_id}` — partial update.
- `DELETE /api/v1/clients/{id}/correspondence/{correspondence_id}` (advisor) — 204.
- `GET /api/v1/clients/{id}/authority-contacts` — filters: `contact_type?`; paginated.
- `POST /api/v1/clients/{id}/authority-contacts` — create (`contact_type`, `name`, `office?`, `phone?`, `email?`, `notes?`).
- `GET /api/v1/clients/{id}/signature-requests` — optional `status` filter; paginated.
- `GET /api/v1/clients/{id}/annual-reports` — list all, newest first.

### Authority contacts (delete = advisor only)

- `GET /api/v1/authority-contacts/{id}` — 404 if missing.
- `PATCH /api/v1/authority-contacts/{id}` — partial update; validates `contact_type` when provided.
- `DELETE /api/v1/authority-contacts/{id}` (advisor) — 204.

---

## Binders (advisor + secretary)

- `POST /api/v1/binders/receive` — intake (`client_id`, `binder_number`, `binder_type`, `received_at`, `received_by`, `notes?`); 201 or 409 on duplicate active binder number.
- `POST /api/v1/binders/{id}/ready` — from `in_office` only; 400 otherwise.
- `POST /api/v1/binders/{id}/return` — `pickup_person_name?`, `returned_by?`; from `ready_for_pickup` only.
- `GET /api/v1/binders` — filters: `status`, `client_id`, `work_state`, `query`, `client_name`, `binder_number`, `year`; sort: `sort_by` (received_at|days_in_office|status|client_name), `sort_dir` (asc|desc); paginated.
- `GET /api/v1/binders/{id}` — single binder with signals/work state; 404 if missing.
- `GET /api/v1/binders/open` — paginated; status != `returned`.
- `GET /api/v1/binders/{id}/history` — audit log; 404 if missing.
- `DELETE /api/v1/binders/{id}` (advisor) — soft-delete; 204.

---

## Dashboard

- `GET /api/v1/dashboard/summary` — counts: `binders_in_office`, `binders_ready_for_pickup`, attention items.
- `GET /api/v1/dashboard/overview` (advisor) — management metrics + quick actions.
- `GET /api/v1/dashboard/attention` — attention items; `unpaid_charge` items advisor-only.
- `GET /api/v1/dashboard/tax-submissions` — optional `tax_year`; submission progress widget.

---

## Search (advisor + secretary)

- `GET /api/v1/search` — filters: `query`, `client_name`, `id_number`, `binder_number`, `signal_type[]`, `has_signals`; paginated.

---

## Charges (billing)

- `POST /api/v1/charges` (advisor) — create (`client_id`, `amount` >0, `charge_type` retainer|one_time, `period?`, `currency` default ILS).
- `POST /api/v1/charges/{id}/issue` (advisor) — from `draft` only.
- `POST /api/v1/charges/{id}/mark-paid` (advisor) — from `issued` only.
- `POST /api/v1/charges/{id}/cancel` (advisor) — body: `reason?`; invalid from `paid` or `canceled`.
- `GET /api/v1/charges` — filters: `client_id`, `status`; paginated. Secretary sees limited fields (no amount/currency).
- `GET /api/v1/charges/{id}` — role-based shaping; 404 if missing.

---

## Permanent Documents

- `POST /api/v1/documents/upload` — multipart: `client_id`, `document_type`, `file`, `tax_year?`, `annual_report_id?`, `notes?`; 201.
- `GET /api/v1/documents/client/{id}` — list documents; optional `tax_year` filter.
- `GET /api/v1/documents/client/{id}/signals` — missing/required doc indicators.
- `GET /api/v1/documents/client/{id}/versions` — version history; required `document_type`, optional `tax_year`.
- `GET /api/v1/documents/{id}/download-url` — returns `{ url }` (presigned/local path).
- `PUT /api/v1/documents/{id}/replace` (advisor) — multipart: `file`; replaces stored file, increments version.
- `POST /api/v1/documents/{id}/approve` (advisor) — marks document approved.
- `POST /api/v1/documents/{id}/reject` (advisor) — body: `notes`; marks document rejected.
- `PATCH /api/v1/documents/{id}/notes` — body: `notes`; update notes on non-deleted document.
- `GET /api/v1/documents/annual-report/{report_id}` — list documents linked to an annual report.
- `DELETE /api/v1/documents/{id}` (advisor) — soft-delete; 204.

---

## Tax Deadlines

- `POST /api/v1/tax-deadlines` — body: `client_id`, `deadline_type`, `due_date`, `payment_amount?`, `description?`; 201.
- `GET /api/v1/tax-deadlines` — filters: `client_id?`, `deadline_type?`, `status?`; paginated.
- `GET /api/v1/tax-deadlines/{id}` — 404 if missing.
- `PUT /api/v1/tax-deadlines/{id}` — update `deadline_type`, `due_date`, `payment_amount?`, `description?`.
- `POST /api/v1/tax-deadlines/{id}/complete` — 400 on invalid state.
- `DELETE /api/v1/tax-deadlines/{id}` — 204.
- `GET /api/v1/tax-deadlines/dashboard/urgent` — urgent and upcoming sets with client names, urgency level, days remaining.
- `GET /api/v1/tax-deadlines/timeline` — query: `client_id`; returns timeline entries with `days_remaining` and `milestone_label`.

---

## Annual Reports (advisor + secretary)

- `POST /api/v1/annual-reports` — create (`client_id`, `tax_year`, `client_type`, `deadline_type`, `assigned_to?`, `notes?`, income flags); 201; 409 on duplicate (client, tax_year); returns `AnnualReportDetailResponse`.
- `GET /api/v1/annual-reports` — filters: `tax_year?`; sort: `sort_by` (tax_year|status|filing_deadline|created_at|client_id), `order` (asc|desc); paginated (default 20, max 200).
- `GET /api/v1/annual-reports/{id}` — full detail with schedules + status history; 404 if missing.
- `DELETE /api/v1/annual-reports/{id}` (advisor) — soft-delete; 204.
- `GET /api/v1/annual-reports/kanban/view` — stage-grouped view.
- `GET /api/v1/annual-reports/overdue` — filing_deadline passed & open statuses; optional `tax_year`.
- `GET /api/v1/annual-reports/{id}/export/pdf` — PDF download of working draft.

### Status & Lifecycle

- `POST /api/v1/annual-reports/{id}/status` — transition with `VALID_TRANSITIONS` enforcement; optional `assessment_amount`, `refund_due`, `tax_due`, `note`, `ita_reference`.
- `POST /api/v1/annual-reports/{id}/submit` — shorthand submit transition; 400 on invalid source status.
- `POST /api/v1/annual-reports/{id}/amend` (advisor) — transition to `amended`; requires `reason`.
- `POST /api/v1/annual-reports/{id}/deadline` — change deadline type (`standard|extended|custom`); optional `custom_deadline_note`.
- `GET /api/v1/annual-reports/{id}/history` — status transition log; 404 if missing.

### Details & Schedules

- `GET /api/v1/annual-reports/{id}/details` — financial detail record; empty shell if none.
- `PATCH /api/v1/annual-reports/{id}/details` — upsert `tax_refund_amount`, `tax_due_amount`, `client_approved_at`, `internal_notes`.
- `POST /api/v1/annual-reports/{id}/schedules` — add schedule entry.
- `POST /api/v1/annual-reports/{id}/schedules/complete` — mark complete; 400 if absent.

### Tax Year Views

- `GET /api/v1/tax-year/{tax_year}/reports` — paginated season list (default 50, max 200).
- `GET /api/v1/tax-year/{tax_year}/summary` — counts per status, completion %, overdue count.

### Annual Report Annex

- `GET /api/v1/annual-reports/{id}/annex/{schedule}` — list annex data lines for schedule.
- `POST /api/v1/annual-reports/{id}/annex/{schedule}` — add annex line; 201.
- `PATCH /api/v1/annual-reports/{id}/annex/{schedule}/{line_id}` — update annex line.
- `DELETE /api/v1/annual-reports/{id}/annex/{schedule}/{line_id}` (advisor) — 204.

### Annual Report Income / Expenses

- `POST /api/v1/annual-reports/{id}/income` — add income line; 201.
- `PATCH /api/v1/annual-reports/{id}/income/{line_id}` — update income line.
- `DELETE /api/v1/annual-reports/{id}/income/{line_id}` (advisor) — 204.
- `POST /api/v1/annual-reports/{id}/expenses` — add expense line; 201.
- `PATCH /api/v1/annual-reports/{id}/expenses/{line_id}` — update expense line.
- `DELETE /api/v1/annual-reports/{id}/expenses/{line_id}` (advisor) — 204.

### Annual Report Financials

- `GET /api/v1/annual-reports/{id}/financials` — financial summary.
- `GET /api/v1/annual-reports/{id}/tax-calculation` — tax calculation.
- `GET /api/v1/annual-reports/{id}/advances-summary` — advances summary.
- `GET /api/v1/annual-reports/{id}/readiness` — readiness check.

---

## Reminders (advisor + secretary)

- `GET /api/v1/reminders` — filters: `status?`, `client_id?`; paginated.
- `GET /api/v1/reminders/{id}` — 404 if missing.
- `POST /api/v1/reminders` — type: `tax_deadline_approaching|binder_idle|unpaid_charge|custom`; required FKs per type (`tax_deadline_id`, `binder_id`, `charge_id`); `client_id`, `target_date`, `days_before` ≥0, `message?`.
- `POST /api/v1/reminders/{id}/cancel` — pending only.

---

## Advance Payments (advisor + secretary)

- `GET /api/v1/advance-payments` — requires `client_id`; optional `year` (defaults current UTC year), `status`; paginated.
- `POST /api/v1/advance-payments` (advisor) — create (`client_id`, `year`, `month`, `due_date`, `expected_amount?`, `paid_amount?`, `tax_deadline_id?`).
- `PATCH /api/v1/advance-payments/{id}` (advisor) — update `paid_amount`, `status`, `expected_amount?`, `notes?`; 404 if not found.
- `DELETE /api/v1/advance-payments/{id}` (advisor) — 204.
- `GET /api/v1/advance-payments/suggest` — query: `client_id`, `year`; returns suggested expected amount.
- `GET /api/v1/advance-payments/overview` — cross-client overview with KPIs; requires `year`.
- `GET /api/v1/advance-payments/chart` — chart data; query: `client_id`, `year`.
- `GET /api/v1/advance-payments/kpi` — annual KPIs; query: `client_id`, `year`.

---

## VAT Reports (prefix `/api/v1/vat`)

- `POST /vat/work-items` — create (`client_id`, `period`, `assigned_to?`, `mark_pending?`, `pending_materials_note?`).
- `POST /vat/work-items/{id}/materials-complete` — `pending_materials → material_received`.
- `POST /vat/work-items/{id}/invoices` — add invoice (`invoice_type`, `invoice_number`, `invoice_date`, `counterparty_name`, `net_amount`, `vat_amount`, `counterparty_id?`, `expense_category?`).
- `GET /vat/work-items/{id}/invoices` — optional `invoice_type` filter.
- `DELETE /vat/work-items/{id}/invoices/{invoice_id}` — not allowed after filing.
- `POST /vat/work-items/{id}/ready-for-review` — `data_entry_in_progress → ready_for_review`.
- `POST /vat/work-items/{id}/send-back` (advisor) — `ready_for_review → data_entry_in_progress`; requires `correction_note`.
- `POST /vat/work-items/{id}/file` (advisor) — finalize filing (`filing_method` manual|online, `override_amount?`, `override_justification?`); locks period.
- `GET /vat/work-items/{id}` — enriched with `client_name`.
- `GET /vat/work-items/{id}/audit` — audit trail.
- `GET /vat/clients/{client_id}/work-items` — all work items for client.
- `GET /vat/work-items` — optional `status` filter; paginated (default 50, max 200).
- `GET /vat/client/{client_id}/summary` — VAT client summary.
- `GET /vat/client/{client_id}/export` (advisor) — export as excel or pdf; requires `year`.

---

## Signature Requests (advisor + secretary)

- `POST /api/v1/signature-requests` — create (`client_id`, `request_type`, `title`, `description?`, `signer_name`, `signer_email?`, `signer_phone?`, `annual_report_id?`, `document_id?`, `content_to_hash?`).
- `GET /api/v1/signature-requests/pending` — paginated.
- `GET /api/v1/signature-requests/{id}` — detail with embedded `audit_trail`; 404 if missing.
- `POST /api/v1/signature-requests/{id}/send` — sets expiry (default 14 days); returns signing token once + `signing_url_hint`.
- `POST /api/v1/signature-requests/{id}/cancel` — optional `reason`.
- `GET /api/v1/signature-requests/{id}/audit-trail`

### Public signing (no JWT)

- `GET /sign/{token}` — record view; returns `{ request_id, title, description, signer_name, status, content_hash, expires_at }` or 400 on invalid/expired.
- `POST /sign/{token}/approve` — records signature; returns `SignerViewResponse`.
- `POST /sign/{token}/decline` — optional `reason`; records decline.

---

## Notifications (advisor + secretary)

- `GET /api/v1/notifications` — filters: `client_id?`, `limit?`; returns list of notifications.
- `GET /api/v1/notifications/unread-count` — optional `client_id`; returns `{ count }`.
- `POST /api/v1/notifications/mark-read` — body: `notification_ids: [int]`; marks specified notifications as read.
- `POST /api/v1/notifications/mark-all-read` — query: `client_id`; marks all unread for client as read.

---

## Reports (advisor only)

- `GET /api/v1/reports/aging` — aging buckets for unpaid charges; optional `as_of_date`.
- `GET /api/v1/reports/aging/export` — query: `format=excel|pdf`, optional `as_of_date`; file download.

---

## Key Enums

| Domain                 | Enum                 | Values                                                                                                                                                                      |
| ---------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Roles                  | —                    | `advisor`, `secretary`                                                                                                                                                      |
| Client type            | `ClientType`         | `osek_patur`, `osek_murshe`, `company`, `employee`                                                                                                                          |
| Client status          | `ClientStatus`       | `active`, `frozen`, `closed`                                                                                                                                                |
| Binder status          | `BinderStatus`       | `in_office`, `ready_for_pickup`, `returned`                                                                                                                                 |
| Binder type            | `BinderType`         | `vat`, `income_tax`, `national_insurance`, `capital_declaration`, `annual_report`, `salary`, `bookkeeping`, `other`                                                         |
| Charge type            | `ChargeType`         | `retainer`, `one_time`                                                                                                                                                      |
| Charge status          | `ChargeStatus`       | `draft`, `issued`, `paid`, `canceled`                                                                                                                                       |
| Tax deadline type      | `DeadlineType`       | `vat`, `advance_payment`, `national_insurance`, `annual_report`, `other`                                                                                                    |
| Tax deadline status    | —                    | `pending`, `completed`                                                                                                                                                      |
| Reminder type          | `ReminderType`       | `tax_deadline_approaching`, `binder_idle`, `unpaid_charge`, `custom`                                                                                                        |
| Reminder status        | `ReminderStatus`     | `pending`, `sent`, `canceled`                                                                                                                                               |
| Annual report status   | `AnnualReportStatus` | `not_started`, `collecting_docs`, `docs_complete`, `in_preparation`, `pending_client`, `submitted`, `amended`, `accepted`, `assessment_issued`, `objection_filed`, `closed` |
| Annual report deadline | `DeadlineType`       | `standard`, `extended`, `custom`                                                                                                                                            |
| VAT work item status   | —                    | `pending_materials`, `material_received`, `data_entry_in_progress`, `ready_for_review`, `filed`                                                                             |
| VAT invoice type       | —                    | `income`, `expense`                                                                                                                                                         |
| VAT filing method      | —                    | `manual`, `online`                                                                                                                                                          |
| Advance payment status | —                    | `pending`, `paid`, `partial`, `overdue`                                                                                                                                     |
| Document type          | `DocumentType`       | `id_copy`, `power_of_attorney`, `engagement_agreement`, `tax_form`, `receipt`, `invoice_doc`, `bank_approval`, `withholding_certificate`, `nii_approval`, `other`           |
| Document status        | —                    | `pending`, `received`, `approved`, `rejected`                                                                                                                               |
| WorkState              | —                    | `WAITING_FOR_WORK`, `IN_PROGRESS`, `COMPLETED`                                                                                                                              |
| Signals                | `SignalType`         | `MISSING_DOCUMENTS`, `READY_FOR_PICKUP`, `UNPAID_CHARGES`, `IDLE_BINDER`                                                                                                    |

---

## Standard HTTP Errors

| Code | Meaning                                              |
| ---- | ---------------------------------------------------- |
| 400  | Invalid input or illegal state transition            |
| 401  | Missing/invalid/expired token                        |
| 403  | Insufficient permissions                             |
| 404  | Resource not found                                   |
| 409  | Conflict (duplicate binder number, user email, etc.) |
| 422  | Request validation failure                           |
