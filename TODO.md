# TODO — Missing Parts in the CRM System (Tax Advisor)

> Based on analysis of `BACKEND_SPEC.md`, `FRONTEND_PROJECT_RULES.md`, and `CLAUDE.md`.  
> Sprints 1–9 are frozen. All items below are documented gaps that have not yet been addressed.

---

## 🔴 Critical — Broken / Non-Working Functionality

### Background Jobs — No scheduler at all
- [ ] **Reminders are not sent automatically** — `Reminder.send_on` is stored but there is no worker triggering it
- [ ] **Signature requests do not expire automatically** — `expire_overdue()` exists in the service but is not scheduled
- [ ] **Notifications are not sent** — `WhatsAppChannel` and `EmailChannel` are stubs only; no real sending
- [ ] **No delivery confirmation webhook** — impossible to know whether a message reached the destination

### Signatures
- [ ] **No document upload in the signing process** — flow exists but the document itself is not uploaded / saved

### Invoices
- [ ] **No API to create an invoice** — `InvoiceService.attach_invoice_to_charge()` exists but without a router; visible only in the timeline

---

## 🟠 High — Major Functional Gaps

### Clients
- [x] No client deletion — soft-delete via `DELETE /clients/{id}` (ADVISOR only)
- [ ] `has_signals` filter loads up to 1,000 clients into memory — no real pagination
- [ ] Client import: no dry-run before insertion

### Binders
- [x] No binder deletion — soft-delete via `DELETE /binders/{id}` (ADVISOR only)
- [ ] `WorkState` calculates notifications per binder on every call — no cache

### Charges
- [x] No soft-delete for charges — soft-delete via `DELETE /charges/{id}` (ADVISOR only, DRAFT only)
- [ ] No mechanism to issue an invoice directly from a charge in the UI

### Permanent Documents
- [ ] No deletion / replacement of an existing document
- [ ] Local storage only (`LocalStorageProvider`) — no S3 / cloud storage
- [ ] Upload loads the entire file into memory — no streaming

### Correspondence
- [x] No pagination — all client correspondence is loaded at once — paginated via `list_by_client_paginated` (already implemented)

### Annual Reports
- [x] No deletion of annual reports — soft-delete via `DELETE /annual-reports/{id}` (ADVISOR only)

### Aging Report
- [ ] No CSV format — only JSON/Excel
- [ ] No streaming — loads up to 10,000 charges into memory

### Timeline
- [ ] No events from tax deadlines in the timeline
- [ ] No events from annual reports in the timeline
- [ ] Full aggregation in memory before pagination

### Search
- [ ] Mixed search (client + binder) loads everything into memory
- [ ] Filtering by `work_state` / `signal_type` loads everything into memory
- [ ] No full-text search / search index

### Advance Payments
- [ ] No API to create an advance payment — manual seeding only
- [ ] Pagination happens in memory after full fetch
- [ ] `AdvancePayment.status` is a string without enum enforcement in the ORM

---

## 🟡 Medium — Infrastructure Gaps

### Security and Authentication
- [ ] No self-service password change
- [ ] No MFA
- [ ] Logout does not invalidate JWT on the server side (client-side only)

### Performance and Infrastructure
- [ ] No rate limiting / throttling on any endpoint
- [ ] No caching on dashboard — recalculated on every request
- [ ] Tax Deadlines without `client_id` — loads everything into memory before pagination

### VAT Reports
- [ ] No uniqueness enforcement for `period` at the DB level (service-level only)

### Users
- [ ] `AuditLogsDrawer` shows only page 1 (20 records) — no pagination in the UI

### Migrations
- [ ] No migration tool for production — every schema change requires manual coordination

---

## 🔵 Low — UX / Polish

- [ ] No UI to resend a failed notification
- [ ] Dashboard quick actions — selects the first entity (heuristic) and not necessarily the correct one
- [ ] No timeline events from tax deadlines and annual reports (also mentioned above)

---

*Updated: Sprint 10 — Not yet addressed*