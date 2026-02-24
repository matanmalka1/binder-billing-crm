# API Contract

## Conventions

- Base path for authenticated business APIs: `/api/v1`. Public meta endpoints: `GET /`, `GET /info`, `GET /health`. Public signing endpoints live under `/sign/*`.
- Auth: `POST /api/v1/auth/login` issues a JWT; clients may send it as `Authorization: Bearer <token>` or rely on the HttpOnly `access_token` cookie set by login. `POST /api/v1/auth/logout` clears the cookie.
- Roles: `advisor` (admin/elevated) and `secretary` (operational). Where `require_role` is present, access is enforced; otherwise any authenticated user is allowed.
- Content types: JSON request/response unless stated; uploads use `multipart/form-data`; downloads return files with appropriate media type headers.
- Pagination: unless noted, `page` defaults to 1 (>=1) and `page_size` defaults to 20 (max 100). Timeline uses `page_size` default 50 (max 200); annual reports by tax year default 50; VAT work-items list defaults 50.

## Service Metadata (no auth)

- `GET /` → `{ service, status }`
- `GET /info` → `{ app, env }`
- `GET /health` → 200 with DB check result, 503 when unhealthy

## Authentication

- `POST /api/v1/auth/login` — body: `email`, `password`, `remember_me?`; returns `{ token, user { id, full_name, role } }` and sets HttpOnly cookie (`remember_me` doubles TTL).
- `POST /api/v1/auth/logout` — clears auth cookie, 204.

## Users (advisor only)

- `POST /api/v1/users` — create (`full_name`, `email`, `role`, `password`, `phone?`); 409 on duplicates.
- `GET /api/v1/users` — paginated list.
- `GET /api/v1/users/{user_id}` — fetch one.
- `PATCH /api/v1/users/{user_id}` — update `full_name`, `phone`, `role`; immutable fields rejected with 400.
- `POST /api/v1/users/{user_id}/activate`
- `POST /api/v1/users/{user_id}/deactivate` — also bumps token version to invalidate sessions.
- `POST /api/v1/users/{user_id}/reset-password` — admin reset + token version bump.
- `GET /api/v1/users/audit-logs` — filters: `action`, `target_user_id`, `actor_user_id`, `email`, `from`, `to`; paginated.

## Clients (advisor + secretary)

- `POST /api/v1/clients` — create client (`full_name`, `id_number`, `client_type`, `opened_at`, `phone?`, `email?`, `notes?`).
- `GET /api/v1/clients` — filters `status`, `has_signals`, `search`; paginated.
- `GET /api/v1/clients/{client_id}` — single client.
- `PATCH /api/v1/clients/{client_id}` — update `full_name`, `phone`, `email`, `notes`, `status` (authorization enforced in service layer).

### Client Excel import/export

- `GET /api/v1/clients/export` — XLSX download of all clients.
- `GET /api/v1/clients/template` — XLSX template download.
- `POST /api/v1/clients/import` — upload XLSX; response `{ created, total_rows, errors[] }`.

### Client tax profile

- `GET /api/v1/clients/{client_id}/tax-profile` — returns profile or empty shell if none.
- `PATCH /api/v1/clients/{client_id}/tax-profile` — fields: `vat_type`, `business_type`, `tax_year_start`, `accountant_name`; `vat_type` validated against enum.

### Client binders & timeline

- `GET /api/v1/clients/{client_id}/binders` — paginated extended binder list; 404 if client missing.
- `GET /api/v1/clients/{client_id}/timeline` — paginated client event feed (default `page_size` 50, max 200).

### Correspondence

- `GET /api/v1/clients/{client_id}/correspondence` — paginated list.
- `POST /api/v1/clients/{client_id}/correspondence` — body: `correspondence_type` enum, `subject`, `occurred_at`, `notes?`, `contact_id?`.

### Authority contacts (advisor + secretary; delete = advisor only)

- `POST /api/v1/clients/{client_id}/authority-contacts` — create (`contact_type`, `name`, `office?`, `phone?`, `email?`, `notes?`).
- `GET /api/v1/clients/{client_id}/authority-contacts` — optional `contact_type` filter.
- `PATCH /api/v1/authority-contacts/{contact_id}` — partial update (validates `contact_type` when provided).
- `DELETE /api/v1/authority-contacts/{contact_id}` — advisor only, 204 on success.

### Signature requests per client

- `GET /api/v1/clients/{client_id}/signature-requests` — optional `status` filter; paginated.

### Annual reports per client

- `GET /api/v1/clients/{client_id}/annual-reports` — list all for client, newest first.

## Binders (advisor + secretary)

- `POST /api/v1/binders/receive` — intake (`client_id`, `binder_number`, `binder_type`, `received_at`, `received_by`, `notes?`); 201 or 409 on duplicate active binder number.
- `POST /api/v1/binders/{binder_id}/ready` — mark ready for pickup (uses caller as actor).
- `POST /api/v1/binders/{binder_id}/return` — optional `pickup_person_name`, `returned_by` (defaults to caller); sets returned state.
- `GET /api/v1/binders` — list active binders; filters `status`, `client_id`, `work_state`; returns signals & available actions.
- `GET /api/v1/binders/{binder_id}` — single binder with signals/work state.
- `GET /api/v1/binders/open` — paginated extended list where `status != returned`.
- `GET /api/v1/binders/{binder_id}/history` — audit log; 404 if binder missing.

## Dashboard

- `GET /api/v1/dashboard/summary` — counts: `binders_in_office`, `binders_ready_for_pickup`, `attention` items.
- `GET /api/v1/dashboard/overview` — advisor only; management metrics + quick actions.
- `GET /api/v1/dashboard/work-queue` — paginated operational queue (binders with work_state/signals).
- `GET /api/v1/dashboard/attention` — items needing attention (role-filtered content).
- `GET /api/v1/dashboard/tax-submissions` — optional `tax_year`; returns submission progress widget.

## Search (advisor + secretary)

- `GET /api/v1/search` — filters: `query`, `client_name`, `id_number`, `binder_number`, `work_state`, `signal_type[]`, `has_signals`; paginated results across clients/binders.

## Charges (billing)

- `POST /api/v1/charges` — advisor only; create (`client_id`, `amount>0`, `charge_type` retainer|one_time, `period?`, `currency` default ILS).
- `POST /api/v1/charges/{charge_id}/issue` — advisor only; only from draft.
- `POST /api/v1/charges/{charge_id}/mark-paid` — advisor only; only from issued.
- `POST /api/v1/charges/{charge_id}/cancel` — advisor only; body `reason?`; invalid from `paid` or already canceled.
- `GET /api/v1/charges` — advisor + secretary; filters `client_id`, `status`; paginated. Advisors receive full fields, secretaries get limited view.
- `GET /api/v1/charges/{charge_id}` — same role-based shaping; 404 if missing.

## Permanent documents

- `POST /api/v1/documents/upload` — multipart with `client_id`, `document_type` (`id_copy|power_of_attorney|engagement_agreement`), `file`; advisor/secretary.
- `GET /api/v1/documents/client/{client_id}` — list documents for client.
- `GET /api/v1/documents/client/{client_id}/signals` — operational indicators for missing/required docs.

## Tax deadlines

- `POST /api/v1/tax-deadlines` — body: `client_id`, `deadline_type` (`vat|advance_payment|national_insurance|annual_report|other`), `due_date`, `payment_amount?`, `description?`; 201.
- `GET /api/v1/tax-deadlines` — filters `client_id?`, `deadline_type?`, `status?`; paginated (defaults 20). Without `client_id`, returns pending/upcoming deadlines across clients.
- `GET /api/v1/tax-deadlines/{deadline_id}` — fetch one or 404.
- `POST /api/v1/tax-deadlines/{deadline_id}/complete` — mark completed; 400 on invalid state.
- `GET /api/v1/tax-deadlines/dashboard/urgent` — urgent and upcoming sets with client names, urgency level, days remaining.

## Annual reports (advisor + secretary)

- `POST /api/v1/annual-reports` — create (`client_id`, `tax_year`, `client_type`, `deadline_type`, `assigned_to?`, `notes?`, flags: `has_rental_income`, `has_capital_gains`, `has_foreign_income`, `has_depreciation`, `has_exempt_rental`); returns detail with schedules/history.
- `GET /api/v1/annual-reports` — optional `tax_year`; paginated (page_size default 20, max 200).
- `GET /api/v1/annual-reports/kanban/view` — grouped-by-stage view.
- `GET /api/v1/annual-reports/overdue` — list overdue (no pagination).
- `GET /api/v1/annual-reports/{report_id}` — full detail (schedules + history) or 404.
- `GET /api/v1/annual-reports/{report_id}/details` — granular financial/tax detail record (empty shell if none).
- `PATCH /api/v1/annual-reports/{report_id}/details` — partial update; validates enums.
- `GET /api/v1/annual-reports/{report_id}/schedules` — list schedule entries.
- `POST /api/v1/annual-reports/{report_id}/schedules` — add schedule entry manually.
- `POST /api/v1/annual-reports/{report_id}/schedules/complete` — mark schedule complete.
- `POST /api/v1/annual-reports/{report_id}/status` — transition status; rejects invalid graph jumps; records history and optional financials (`assessment_amount`, `refund_due`, `tax_due`, `note`, `ita_reference`).
- `POST /api/v1/annual-reports/{report_id}/submit` — convenience to set status `submitted`, optional `submitted_at` and `ita_reference`/`note`.
- `POST /api/v1/annual-reports/{report_id}/deadline` — change deadline type (`standard|extended|custom`) with optional `custom_deadline_note`.
- `POST /api/v1/annual-reports/{report_id}/transition` — UI helper mapping stages → statuses; auto intermediate step when needed.
- `GET /api/v1/annual-reports/{report_id}/history` — status history list.
- `GET /api/v1/tax-year/{tax_year}/reports` — paginated season list (page_size default 50, max 200).
- `GET /api/v1/tax-year/{tax_year}/summary` — aggregate counts, completion rate, overdue count.

## Reminders (advisor + secretary)

- `GET /api/v1/reminders` — optional `status` (`pending|sent|canceled`); paginated.
- `GET /api/v1/reminders/{reminder_id}` — fetch one or 404.
- `POST /api/v1/reminders` — create reminder of type `tax_deadline_approaching|binder_idle|unpaid_charge|custom`; required foreign keys per type (`tax_deadline_id`, `binder_id`, or `charge_id`), `client_id`, `target_date`, `days_before`, `message?`.
- `POST /api/v1/reminders/{reminder_id}/cancel` — cancel pending reminder.
- `POST /api/v1/reminders/{reminder_id}/mark-sent` — mark as sent (used by jobs/ops).

## Reports (advisor only)

- `GET /api/v1/reports/aging` — aging buckets for unpaid charges; optional `as_of_date`.
- `GET /api/v1/reports/aging/export` — query `format=excel|pdf`, optional `as_of_date`; file download.

## Timeline (advisor + secretary)

- `GET /api/v1/clients/{client_id}/timeline` — unified event feed; paginated (default size 50, max 200).

## Advance payments (advisor + secretary)

- `GET /api/v1/advance-payments` — requires `client_id`; optional `year` (defaults current UTC year); paginated.
- `POST /api/v1/advance-payments` — create (`client_id`, `year`, `month`, `due_date`, `expected_amount?`, `paid_amount?`, `tax_deadline_id?`).
- `PATCH /api/v1/advance-payments/{payment_id}` — update `paid_amount`, `status` (`pending|paid|partial|overdue`); 404 if not found, 400 on invalid status.

## VAT reports (VAT work items)

Prefix `/api/v1/vat`.

- `POST /vat/work-items` — create work item (`client_id`, `period`, `assigned_to?`, `mark_pending?`, `pending_materials_note?`). Authenticated user required.
- `POST /vat/work-items/{item_id}/materials-complete` — mark `pending_materials → material_received`.
- `POST /vat/work-items/{item_id}/invoices` — add invoice (`invoice_type` income|expense, `invoice_number`, `invoice_date`, `counterparty_name`, `net_amount`, `vat_amount`, `counterparty_id?`, `expense_category?`); accessible to authenticated users (intended for secretary/advisor).
- `GET /vat/work-items/{item_id}/invoices` — optional `invoice_type` filter; list invoices.
- `DELETE /vat/work-items/{item_id}/invoices/{invoice_id}` — delete invoice (not allowed after filing).
- `POST /vat/work-items/{item_id}/ready-for-review` — set `data_entry_in_progress → ready_for_review`.
- `POST /vat/work-items/{item_id}/send-back` — advisor only; move `ready_for_review → data_entry_in_progress` with `correction_note`.
- `POST /vat/work-items/{item_id}/file` — advisor only; finalize filing (`filing_method` manual|online, optional `override_amount` with justification); sets status `filed` and locks period.
- `GET /vat/work-items/{item_id}` — single work item enriched with `client_name`.
- `GET /vat/clients/{client_id}/work-items` — all work items for a client.
- `GET /vat/work-items` — optional `status` filter; paginated (default page_size 50).
- `GET /vat/work-items/{item_id}/audit` — audit trail entries.

## Signature requests (advisor + secretary unless noted)

- `POST /api/v1/signature-requests` — create (`client_id`, `request_type`, `title`, `description?`, `signer_name`, `signer_email?`, `signer_phone?`, `annual_report_id?`, `document_id?`, `content_to_hash?`).
- `GET /api/v1/signature-requests/pending` — paginated pending list.
- `GET /api/v1/signature-requests/{request_id}` — detail with audit trail embedded; 404 if not found.
- `POST /api/v1/signature-requests/{request_id}/send` — set expiry (default 14 days); returns signing token once plus `signing_url_hint`.
- `POST /api/v1/signature-requests/{request_id}/cancel` — optional `reason`.
- `GET /api/v1/signature-requests/{request_id}/audit-trail` — full audit events list.

### Public signing (no JWT)

- `GET /sign/{token}` — record view and return minimal signing payload (title, signer_name, status, content_hash, expires_at).
- `POST /sign/{token}/approve` — record signature; returns updated signer view payload.
- `POST /sign/{token}/decline` — optional `reason`; records decline.

## Key enums (for reference)

- Roles: `advisor`, `secretary`.
- Binder status: `in_office`, `ready_for_pickup`, `returned`; Binder type includes `vat`, `income_tax`, `national_insurance`, `capital_declaration`, `annual_report`, `salary`, `bookkeeping`, `other`.
- Charge type/status: `retainer`/`one_time`; `draft`, `issued`, `paid`, `canceled`.
- Tax deadline type/status: `vat`, `advance_payment`, `national_insurance`, `annual_report`, `other`; status `pending|completed`.
- Reminder type/status: `tax_deadline_approaching`, `binder_idle`, `unpaid_charge`, `custom`; `pending|sent|canceled`.
- Annual report status (workflow): `not_started`, `collecting_docs`, `docs_complete`, `in_preparation`, `pending_client`, `submitted`, `accepted`, `assessment_issued`, `objection_filed`, `closed`. Deadline types: `standard|extended|custom`.
- VAT work item status: `pending_materials`, `material_received`, `data_entry_in_progress`, `ready_for_review`, `filed`; Invoice type `income|expense`; Filing method `manual|online`.
- Advance payment status: `pending`, `paid`, `partial`, `overdue`.
- Permanent document types: `id_copy`, `power_of_attorney`, `engagement_agreement`.

## Standard error codes

- `400` invalid input or illegal state transition
- `401` missing/invalid token
- `403` insufficient permissions
- `404` not found
- `409` conflict (e.g., duplicate binder number or user email)
