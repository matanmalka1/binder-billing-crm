# API Contract

## Conventions

- Base path: `/api/v1`. Public meta: `GET /`, `GET /info`, `GET /health`. Public signing: `/sign/*`.
- Auth: `POST /api/v1/auth/login` issues JWT; send as `Authorization: Bearer <token>` or via HttpOnly `access_token` cookie. `POST /api/v1/auth/logout` clears cookie.
- Roles: `advisor` (elevated) and `secretary` (operational). `require_role` enforces where noted; otherwise any authenticated user may access.
- Content types: JSON unless stated; uploads use `multipart/form-data`; downloads return files with appropriate headers.
- Pagination: `page` (default 1) and `page_size` (default 20, max 100) unless noted. Exceptions: timeline/annual-report season default 50; VAT work-items default 50.
- Error envelope: `{ "detail": "...", "error": { "type": "...", "detail": "...", "status_code": N } }`.

---

## Service Metadata (no auth)

- `GET /` → `{ service, status }`
- `GET /info` → `{ app, env }`
- `GET /health` → 200 with DB result, 503 when unhealthy

---

## Authentication

- `POST /api/v1/auth/login` — body: `email`, `password`, `remember_me?`; returns `{ token, user { id, full_name, role } }`; sets HttpOnly cookie (`remember_me` doubles TTL).
- `POST /api/v1/auth/logout` — clears auth cookie; 204.

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

- `POST /api/v1/clients` — create (`full_name`, `id_number`, `client_type`, `opened_at`, `phone?`, `email?`, `notes?`); 409 on duplicate `id_number`.
- `GET /api/v1/clients` — filters: `status`, `has_signals`, `search`; paginated.
- `GET /api/v1/clients/{id}` — 404 if missing.
- `PATCH /api/v1/clients/{id}` — update `full_name`, `phone`, `email`, `notes`, `status`; advisor required for `frozen`/`closed`.

### Excel import/export

- `GET /api/v1/clients/export` — XLSX download.
- `GET /api/v1/clients/template` — XLSX template download.
- `POST /api/v1/clients/import` (advisor) — multipart XLSX; returns `{ created, total_rows, errors[] }`.

### Sub-resources

- `GET /api/v1/clients/{id}/tax-profile` — empty shell if none; 404 if client missing.
- `PATCH /api/v1/clients/{id}/tax-profile` — fields: `vat_type`, `business_type`, `tax_year_start`, `accountant_name`.
- `GET /api/v1/clients/{id}/binders` — paginated extended binder list; 404 if client missing.
- `GET /api/v1/clients/{id}/timeline` — paginated event feed (default page_size 50, max 200).
- `GET /api/v1/clients/{id}/correspondence` — paginated list ordered by `occurred_at` desc.
- `POST /api/v1/clients/{id}/correspondence` — body: `correspondence_type`, `subject`, `occurred_at`, `notes?`, `contact_id?`; 400 if `contact_id` not linked to client.
- `GET /api/v1/clients/{id}/authority-contacts` — optional `contact_type` filter.
- `POST /api/v1/clients/{id}/authority-contacts` — create (`contact_type`, `name`, `office?`, `phone?`, `email?`, `notes?`).
- `GET /api/v1/clients/{id}/signature-requests` — optional `status` filter; paginated.
- `GET /api/v1/clients/{id}/annual-reports` — list all, newest first.

### Authority contacts (delete = advisor only)

- `PATCH /api/v1/authority-contacts/{id}` — partial update; validates `contact_type` when provided.
- `DELETE /api/v1/authority-contacts/{id}` — advisor only; 204.

---

## Binders (advisor + secretary)

- `POST /api/v1/binders/receive` — intake (`client_id`, `binder_number`, `binder_type`, `received_at`, `received_by`, `notes?`); 201 or 409 on duplicate active binder number.
- `POST /api/v1/binders/{id}/ready` — from `in_office` or `overdue`; 400 otherwise.
- `POST /api/v1/binders/{id}/return` — `pickup_person_name?`, `returned_by?`; from `ready_for_pickup` or `overdue`.
- `GET /api/v1/binders` — filters: `status`, `client_id`, `work_state`; returns signals & available actions.
- `GET /api/v1/binders/{id}` — single binder with signals/work state; 404 if missing.
- `GET /api/v1/binders/open` — paginated; status != `returned`.
- `GET /api/v1/binders/{id}/history` — audit log; 404 if missing.

---

## Dashboard

- `GET /api/v1/dashboard/summary` — counts: `binders_in_office`, `binders_ready_for_pickup`, attention items.
- `GET /api/v1/dashboard/overview` (advisor) — management metrics + quick actions.
- `GET /api/v1/dashboard/work-queue` — paginated operational queue with `work_state`/signals.
- `GET /api/v1/dashboard/attention` — attention items; `unpaid_charge` items advisor-only.
- `GET /api/v1/dashboard/tax-submissions` — optional `tax_year`; submission progress widget.

---

## Search (advisor + secretary)

- `GET /api/v1/search` — filters: `query`, `client_name`, `id_number`, `binder_number`, `work_state`, `signal_type[]`, `has_signals`; paginated.

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

- `POST /api/v1/documents/upload` — multipart: `client_id`, `document_type`, `file`.
- `GET /api/v1/documents/client/{id}` — list documents.
- `GET /api/v1/documents/client/{id}/signals` — missing/required doc indicators.

---

## Tax Deadlines

- `POST /api/v1/tax-deadlines` — body: `client_id`, `deadline_type`, `due_date`, `payment_amount?`, `description?`; 201.
- `GET /api/v1/tax-deadlines` — filters: `client_id?`, `deadline_type?`, `status?`; paginated.
- `GET /api/v1/tax-deadlines/{id}` — 404 if missing.
- `POST /api/v1/tax-deadlines/{id}/complete` — 400 on invalid state.
- `GET /api/v1/tax-deadlines/dashboard/urgent` — urgent and upcoming sets with client names, urgency level, days remaining.

---

## Annual Reports (advisor + secretary)

- `POST /api/v1/annual-reports` — create (`client_id`, `tax_year`, `client_type`, `deadline_type`, `assigned_to?`, `notes?`, income flags); 409 on duplicate (client, tax_year).
- `GET /api/v1/annual-reports` — optional `tax_year`; paginated (default 20, max 200).
- `GET /api/v1/annual-reports/{id}` — full detail with schedules + status history; 404 if missing.
- `GET /api/v1/annual-reports/kanban/view` — stage-grouped view.
- `GET /api/v1/annual-reports/overdue` — filing_deadline passed & open statuses.
- `GET /api/v1/annual-reports/{id}/details` — financial detail record; empty shell if none.
- `PATCH /api/v1/annual-reports/{id}/details` — upsert `tax_refund_amount`, `tax_due_amount`, `client_approved_at`, `internal_notes`.
- `GET /api/v1/annual-reports/{id}/schedules`
- `POST /api/v1/annual-reports/{id}/schedules` — add schedule entry.
- `POST /api/v1/annual-reports/{id}/schedules/complete` — mark complete; 400 if absent.
- `POST /api/v1/annual-reports/{id}/status` — transition with `VALID_TRANSITIONS` enforcement; optional `assessment_amount`, `refund_due`, `tax_due`, `note`, `ita_reference`.
- `POST /api/v1/annual-reports/{id}/submit` — convenience shortcut to `submitted`; optional `submitted_at`, `ita_reference`, `note`.
- `POST /api/v1/annual-reports/{id}/deadline` — change deadline type (`standard|extended|custom`); optional `custom_deadline_note`.
- `POST /api/v1/annual-reports/{id}/transition` — UI stage shortcut; auto-inserts `collecting_docs` step when jumping from `not_started`.
- `GET /api/v1/annual-reports/{id}/history` — status history list; 404 if report missing.
- `GET /api/v1/tax-year/{tax_year}/reports` — paginated season list (default 50, max 200).
- `GET /api/v1/tax-year/{tax_year}/summary` — counts per status, completion %, overdue count.

---

## Reminders (advisor + secretary)

- `GET /api/v1/reminders` — optional `status` filter; paginated.
- `GET /api/v1/reminders/{id}` — 404 if missing.
- `POST /api/v1/reminders` — type: `tax_deadline_approaching|binder_idle|unpaid_charge|custom`; required FKs per type (`tax_deadline_id`, `binder_id`, `charge_id`); `client_id`, `target_date`, `days_before` ≥0, `message?`.
- `POST /api/v1/reminders/{id}/cancel` — pending only.
- `POST /api/v1/reminders/{id}/mark-sent` — pending only; stamps `sent_at`.

---

## Advance Payments (advisor + secretary)

- `GET /api/v1/advance-payments` — requires `client_id`; optional `year` (defaults current UTC year); paginated.
- `POST /api/v1/advance-payments` — create (`client_id`, `year`, `month`, `due_date`, `expected_amount?`, `paid_amount?`, `tax_deadline_id?`).
- `PATCH /api/v1/advance-payments/{id}` — update `paid_amount`, `status`; 404 if not found.

---

## VAT Reports (prefix `/api/v1/vat`)

- `POST /vat/work-items` — create (`client_id`, `period`, `assigned_to?`, `mark_pending?`, `pending_materials_note?`).
- `POST /vat/work-items/{id}/materials-complete` — `pending_materials → material_received`.
- `POST /vat/work-items/{id}/invoices` — add invoice (`invoice_type`, `invoice_number`, `invoice_date`, `counterparty_name`, `net_amount`, `vat_amount`, `counterparty_id?`, `expense_category?`).
- `GET /vat/work-items/{id}/invoices` — optional `invoice_type` filter.
- `DELETE /vat/work-items/{id}/invoices/{invoice_id}` — not allowed after filing.
- `POST /vat/work-items/{id}/ready-for-review` — `data_entry_in_progress → ready_for_review`.
- `POST /vat/work-items/{id}/send-back` (advisor) — `ready_for_review → data_entry_in_progress`; requires `correction_note`.
- `POST /vat/work-items/{id}/file` (advisor) — finalize filing (`filing_method` manual|online, `override_amount?`); locks period.
- `GET /vat/work-items/{id}` — enriched with `client_name`.
- `GET /vat/clients/{client_id}/work-items` — all work items for client.
- `GET /vat/work-items` — optional `status` filter; paginated (default 50).
- `GET /vat/work-items/{id}/audit` — audit trail.

---

## Signature Requests (advisor + secretary)

- `POST /api/v1/signature-requests` — create (`client_id`, `request_type`, `title`, `description?`, `signer_name`, `signer_email?`, `signer_phone?`, `annual_report_id?`, `document_id?`, `content_to_hash?`).
- `GET /api/v1/signature-requests/pending` — paginated.
- `GET /api/v1/signature-requests/{id}` — detail with embedded `audit_trail`; 404 if missing.
- `POST /api/v1/signature-requests/{id}/send` — sets expiry (default 14 days); returns signing token once + `signing_url_hint`.
- `POST /api/v1/signature-requests/{id}/cancel` — optional `reason`.
- `GET /api/v1/signature-requests/{id}/audit-trail`

### Public signing (no JWT)

- `GET /sign/{token}` — record view; returns `{ title, signer_name, status, content_hash, expires_at }` or 400 on invalid/expired.
- `POST /sign/{token}/approve` — records signature; returns updated signer payload.
- `POST /sign/{token}/decline` — optional `reason`; records decline.

---

## Reports (advisor only)

- `GET /api/v1/reports/aging` — aging buckets for unpaid charges; optional `as_of_date`.
- `GET /api/v1/reports/aging/export` — query: `format=excel|pdf`, optional `as_of_date`; file download.

---

## Key Enums

| Domain                 | Enum                 | Values                                                                                                                                                           |
| ---------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Roles                  | —                    | `advisor`, `secretary`                                                                                                                                           |
| Binder status          | `BinderStatus`       | `in_office`, `ready_for_pickup`, `returned`                                                                                                                      |
| Binder type            | `BinderType`         | `vat`, `income_tax`, `national_insurance`, `capital_declaration`, `annual_report`, `salary`, `bookkeeping`, `other`                                              |
| Charge type            | `ChargeType`         | `retainer`, `one_time`                                                                                                                                           |
| Charge status          | `ChargeStatus`       | `draft`, `issued`, `paid`, `canceled`                                                                                                                            |
| Tax deadline type      | `DeadlineType`       | `vat`, `advance_payment`, `national_insurance`, `annual_report`, `other`                                                                                         |
| Tax deadline status    | —                    | `pending`, `completed`                                                                                                                                           |
| Reminder type          | `ReminderType`       | `tax_deadline_approaching`, `binder_idle`, `unpaid_charge`, `custom`                                                                                             |
| Reminder status        | `ReminderStatus`     | `pending`, `sent`, `canceled`                                                                                                                                    |
| Annual report status   | `AnnualReportStatus` | `not_started`, `collecting_docs`, `docs_complete`, `in_preparation`, `pending_client`, `submitted`, `accepted`, `assessment_issued`, `objection_filed`, `closed` |
| Annual report deadline | `DeadlineType`       | `standard`, `extended`, `custom`                                                                                                                                 |
| VAT work item status   | —                    | `pending_materials`, `material_received`, `data_entry_in_progress`, `ready_for_review`, `filed`                                                                  |
| VAT invoice type       | —                    | `income`, `expense`                                                                                                                                              |
| VAT filing method      | —                    | `manual`, `online`                                                                                                                                               |
| Advance payment status | —                    | `pending`, `paid`, `partial`, `overdue`                                                                                                                          |
| Document type          | `DocumentType`       | `id_copy`, `power_of_attorney`, `engagement_agreement`                                                                                                           |
| WorkState              | —                    | `WAITING_FOR_WORK`, `IN_PROGRESS`, `COMPLETED`                                                                                                                   |
| Signals                | —                    | `MISSING_DOCS`, `OVERDUE`, `READY_FOR_PICKUP`, `UNPAID_CHARGES`, `IDLE_BINDER`                                                                                   |

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
