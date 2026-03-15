# Sprint 11 — TODO

> Rules: max 150 lines/file · ORM only · API → Service → Repository · Alembic for all model changes · `require_role()` at endpoint level · background jobs idempotent
> Frontend repo: `../frontend/` — React 19 + TypeScript + React Query + TailwindCSS v4
before any task read claude.md if the task is on backend read claude.md on backend if the task in frontend read claude.md frontend 
---

## 🔴 קריטי

### 1. יצירת דדליינים אוטומטית

**Backend**
- [x] `app/tax_deadline/services/deadline_generator.py` (new) — `generate_vat_deadlines(client_id, year)`, `generate_advance_payment_deadlines(client_id, year)`, `generate_annual_report_deadline(client_id, year)`
- [x] Read `app/clients/models/` + `app/clients/services/` for `ClientTaxProfile.vat_type` (MONTHLY|BIMONTHLY|EXEMPT) to determine VAT cycle
- [x] Read `app/tax_deadline/services/tax_deadline_service.py` for existing `create_deadline()` — reuse it
- [x] `app/tax_deadline/api/` — add `POST /api/v1/tax-deadlines/generate` endpoint: `{client_id, year}` → creates all deadlines for year, skips existing (idempotent)
- [x] Alembic migration only if model changes needed (likely not)

**Frontend**
- [x] `src/features/taxDeadlines/components/` — add "צור דדליינים לשנה" button (ADVISOR only)
- [x] `src/api/taxDeadlines.api.ts` — add `generateDeadlines(clientId, year)` call
- [x] Show success toast with count of created deadlines

---

### 2. יצירת מקדמות אוטומטית (12 payments לשנה)

**Backend**
- [x] `app/advance_payments/services/advance_payment_generator.py` (new) — `generate_annual_schedule(client_id, year)`:
  - Call existing `suggest_expected_amount()` for the amount
  - Create 12 `AdvancePayment` records (months 1–12), skip existing (idempotent)
  - Due date: 15th of each month (Israeli standard)
- [x] `app/advance_payments/api/` — add `POST /api/v1/advance-payments/generate` endpoint: `{client_id, year}`
- [x] Read `app/advance_payments/services/advance_payment_service.py` — reuse `create_payment()`

**Frontend**
- [x] `src/features/advancedPayments/components/` — add "צור לוח מקדמות לשנה" button in `ClientAdvancePaymentsTab`
- [x] `src/api/advancePayments.api.ts` — add `generateSchedule(clientId, year)` call
- [x] Invalidate advance payments query on success

---

### 3. דוחות חסרים

#### 3a. דוח סטטוס דוחות שנתיים

**Backend**
- [x] `app/reports/services/annual_report_status_report.py` (new) — `get_annual_report_status_report(tax_year)`:
  - Group clients by annual report status (NOT_STARTED, COLLECTING_DOCS, IN_PREPARATION, SUBMITTED, CLOSED, etc.)
  - Return: per-status counts + list of clients per status with `client_name`, `form_type`, `filing_deadline`, `days_until_deadline`
- [x] `app/reports/api/` — add `GET /api/v1/reports/annual-reports?tax_year=YYYY`
- [x] Read `app/annual_reports/repositories/` for existing query patterns to reuse

**Frontend**
- [x] `src/pages/reports/AnnualReportStatusReport.tsx` (new page)
- [x] `src/features/reports/components/AnnualReportStatusTable.tsx` (new)
- [x] `src/api/reports.api.ts` — add `getAnnualReportStatusReport(taxYear)`
- [x] `src/router/AppRoutes.tsx` — add route `/reports/annual-reports`
- [x] Add link in sidebar/nav

#### 3b. דוח גבייה — Advance Payments

**Backend**
- [x] `app/reports/services/advance_payment_report.py` (new) — `get_collections_report(year, month?)`:
  - Per client: expected vs. paid vs. overdue
  - Totals: collection_rate %, total_gap
- [x] `app/reports/api/` — add `GET /api/v1/reports/advance-payments?year=YYYY&month=MM`
- [x] Read `app/advance_payments/repositories/` for existing analytics queries to reuse

**Frontend**
- [x] `src/pages/reports/AdvancePaymentCollectionsReport.tsx` (new page)
- [x] `src/api/reports.api.ts` — add `getAdvancePaymentReport(year, month?)`
- [x] `src/router/AppRoutes.tsx` — add route `/reports/advance-payments`

#### 3c. דוח VAT Compliance

**Backend**
- [x] `app/reports/services/vat_compliance_report.py` (new) — `get_vat_compliance_report(year)`:
  - Per client: periods expected vs. filed, on-time vs. late
  - Flag: clients with PENDING_MATERIALS older than 30 days
- [x] `app/reports/api/` — add `GET /api/v1/reports/vat-compliance?year=YYYY`
- [x] Read `app/vat_reports/repositories/` for existing queries

**Frontend**
- [x] `src/pages/reports/VatComplianceReport.tsx` (new page)
- [x] `src/api/reports.api.ts` — add `getVatComplianceReport(year)`
- [x] `src/router/AppRoutes.tsx` — add route `/reports/vat-compliance`

---

## 🟡 חשוב

### 4. Auto-generate reminders בעת יצירת deadline/charge

**Backend**
- [ ] `app/tax_deadline/services/tax_deadline_service.py` — after `create_deadline()` succeeds, call `ReminderService.create_tax_deadline_reminder()` (7 days before)
- [ ] `app/charge/services/billing_service.py` — after `issue_charge()` succeeds, call `ReminderService.create_unpaid_charge_reminder()` (30 days after issue)
- [ ] Read `app/reminders/services/factory.py` for existing creation signatures
- [ ] No model changes, no migration

**Frontend** — no changes needed (reminders appear automatically in RemindersTable)

---

### 5. Document expiration alerts (POA / Engagement Agreement)

**Backend**
- [ ] `app/permanent_documents/models/permanent_document.py` — add `expires_at: Date | None` field
- [ ] Alembic migration: `0022_add_document_expires_at.py`
- [ ] `app/permanent_documents/services/permanent_document_service.py` — expose `expires_at` in response schema
- [ ] `app/core/background_jobs.py` — add `daily_document_expiry_check()`: query docs where `expires_at <= today + 30 days`, create `CUSTOM` reminder per client

**Frontend**
- [ ] `src/features/documents/components/DocumentsUploadCard.tsx` — add optional `expires_at` date picker
- [ ] `src/features/documents/components/DocumentsDataCards.tsx` — show expiry badge if `expires_at` within 30 days

---

### 6. Bulk client operations (freeze / close)

**Backend**
- [ ] `app/clients/api/` — add `POST /api/v1/clients/bulk-action`: `{client_ids: [], action: "freeze"|"close"|"activate"}`
- [ ] `app/clients/services/client_service.py` — add `bulk_update_status(client_ids, status)` — reuse existing `update_client()`
- [ ] ADVISOR only. Return per-item success/failure (same pattern as `POST /api/v1/charges/bulk-action`)

**Frontend**
- [ ] `src/features/clients/components/` — add checkbox column + bulk toolbar to clients table (same pattern as charges bulk toolbar)
- [ ] `src/api/clients.api.ts` — add `bulkAction(clientIds, action)`

---

### 7. Client notes — verify & expose

**Backend**
- [ ] Read `app/clients/schemas/client.py` — confirm `notes` is in `ClientResponse`
- [ ] Read `app/clients/api/clients.py` — confirm PATCH exposes `notes` field

**Frontend**
- [ ] Read `src/features/clients/components/ClientInfoSection.tsx` — if `notes` not shown, add textarea field (edit mode) + display (read mode)

---

## 🟢 נוח

### 8. ClientStatusCard drill-down links

**Frontend only**
- [?] Read `src/features/clients/components/ClientStatusCard.tsx`
- [?] Each tile should navigate: VAT tile → `/clients/:id` (vat tab), charges tile → `/clients/:id` (charges tab), etc.
- [?] Use `useNavigate()` + existing tab param pattern from `ClientDetails.tsx`

---

### 9. Signature request auto-trigger from PENDING_CLIENT

**Backend**
- [ ] `app/annual_reports/services/status_service.py` — on transition to `PENDING_CLIENT`, call `SignatureRequestService.create_request()` with type `ANNUAL_REPORT_APPROVAL`
- [ ] Read `app/signature_requests/services/` for `create_request()` signature
- [ ] No model changes

**Frontend** — no changes (signature request appears automatically in SignatureRequestsPage)

---

## ✅ Completed (Sprint 10)

- VAT export button (frontend)
- Daily reminder scheduler (`background_jobs.py`)
- Storage documentation
- Manual notification send (UI + backend endpoint)
- Bulk charges actions
- Document search
- Permanent documents versioning + approve/reject
- Documents UI versioning
