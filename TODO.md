# Sprint 10 — TODO

> **Baseline:** Sprints 1–9 are frozen and production-ready.  
> **Stack:** FastAPI + SQLAlchemy (backend) · React 19 + TypeScript + TailwindCSS v4 (frontend)  
> **Rules:** Max 150 lines/file · ORM-only · strict layer order API → Service → Repository · Hebrew UI only

---

## Feature 1 — VAT Summary per Client

### Backend
- [x] Create `app/vat_reports/schemas/vat_client_summary_schema.py`
  - `VatPeriodRow` — period, status, total_output_vat, total_input_vat, net_vat, final_vat_amount, filed_at
  - `VatAnnualSummary` — year, total_output_vat, total_input_vat, net_vat, periods_count, filed_count
  - `VatClientSummaryResponse` — client_id, periods: list[VatPeriodRow], annual: list[VatAnnualSummary]
- [x] Create `app/vat_reports/repositories/vat_client_summary_repository.py`
  - `get_periods_for_client(client_id)` — query VatWorkItem ordered by period desc
  - `get_annual_aggregates(client_id)` — group by year, sum vat fields, count periods/filed
- [x] Create `app/vat_reports/services/vat_client_summary_service.py`
  - Validate client exists (raise 404 if not)
  - Call repository, assemble response
- [x] Add route to `app/vat_reports/api/vat_reports.py`
  - `GET /api/v1/vat-reports/client/{client_id}/summary`
  - Roles: ADVISOR + SECRETARY

### Frontend
- [x] Add `ENDPOINTS.vatClientSummary` in `src/api/endpoints.ts`
- [x] Add `vatReportsApi.getClientSummary(clientId)` in `src/api/vatReports.api.ts`
- [x] Add `QK.tax.vatWorkItems.clientSummary(clientId)` in `src/lib/queryKeys.ts`
- [x] Create `src/features/vatReports/components/VatClientSummaryPanel.tsx`
  - Table: תקופה · סטטוס · עסקאות · תשומות · נטו · סופי · הוגש
  - Annual summary cards below table (year, total net, filed/total periods)
  - Use existing `Card`, `DataTable`, `Badge` ui/ components
- [x] Wire panel into client detail page under tab "מע״מ" (create tab if missing)

---

## Feature 2 — VAT Export per Client

### Backend
- [x] Create `app/vat_reports/services/vat_export_service.py` (≤150 lines)
  - `export_to_excel(client_id, year)` — openpyxl, sheet name "מע״מ {year}", columns + totals row
  - `export_to_pdf(client_id, year)` — reportlab, RTL layout, client name + year header, totals row, generated_at footer
  - Both return `{ filepath, filename, format, generated_at }`
- [x] Add route to `app/vat_reports/api/vat_reports.py`
  - `GET /api/v1/vat-reports/client/{client_id}/export?format=excel|pdf&year=YYYY`
  - Returns `FileResponse` with correct `Content-Disposition`
  - Role: ADVISOR only

### Frontend
- [x] Add `ENDPOINTS.vatClientExport(clientId)` in `src/api/endpoints.ts`
- [x] Add `vatReportsApi.exportClientVat(clientId, format, year)` in `src/api/vatReports.api.ts`
  - Follow same blob → link-click pattern as `reportsApi.exportAgingReport`
- [x] Add export controls to `VatClientSummaryPanel`
  - Year selector (default: current year)
  - Two buttons: "ייצוא Excel" · "ייצוא PDF"
  - Show loading state on button during download

---

## Feature 3 — Advance Payments Create API + UI

### Backend
- [x] Add `AdvancePaymentCreateRequest` schema to `app/advance_payments/schemas/`
  - Fields: client_id (int), year (int), month (int 1–12), amount (Decimal), status (optional)
- [x] Add `create_advance_payment(payload)` to `app/advance_payments/repositories/`
  - Raise 409 on unique (client_id, year, month) conflict
- [x] Add `create(payload)` to `app/advance_payments/services/`
  - Validate client exists (404 if not)
  - Validate month in 1–12 (400 if not)
  - Call repo; propagate 409
- [x] Add route `POST /api/v1/advance-payments/` to `app/advance_payments/api/`
  - Role: ADVISOR only
  - Return 201 + created object

### Frontend
- [x] Add `ENDPOINTS.advancePayments` in `src/api/endpoints.ts` (if not present)
- [x] Add `advancePaymentsApi.create(payload)` in `src/api/advancePayments.api.ts`
- [x] In client detail "מקדמות" section:
  - Add "הוסף מקדמה" button — visible to ADVISOR only (check `useAuthStore`)
  - Create modal form with: year (number input), month (select, Hebrew labels), amount (number input)
  - Validate with Zod schema before submit
  - On success: `toast.success`, invalidate `QK.tax.advancePayments.forClientYear`
  - On 409: show "מקדמה לחודש זה כבר קיימת"
  - Use existing `Modal`, `Input`, `Select`, `Button` ui/ components

---

## Feature 4 — Comprehensive Client Status Card

> **Depends on:** Feature 1 (VAT summary endpoint must exist)

### Backend
- [x] Create `app/clients/services/status_card_service.py`
  - Query VatWorkItem for current year → net_vat total, periods filed/total, latest period
  - Query AnnualReport for current year → status, form_type, filing_deadline, refund_due, tax_due
  - Query Charge for ISSUED status → total_outstanding, unpaid_count
  - Query AdvancePayment for current year → total_paid, count
  - Query Binder → active_count, in_office_count
  - Assemble single response object
- [x] Add Pydantic schema `ClientStatusCardResponse` in `app/clients/schemas/`
- [x] Add route `GET /api/v1/clients/{client_id}/status-card` in `app/clients/api/client_status_card.py`
  - Roles: ADVISOR + SECRETARY

### Frontend
- [x] Add `ENDPOINTS.clientStatusCard(clientId)` in `src/api/endpoints.ts`
- [x] Add `clientsApi.getStatusCard(clientId)` in `src/api/clients.api.ts`
- [x] Add `QK.clients.statusCard(clientId)` in `src/lib/queryKeys.ts`
- [x] Create `src/features/clients/components/ClientStatusCard.tsx`
  - 2×3 grid of summary tiles
  - Tiles: מע״מ שנה נוכחית · דוח שנתי · חיובים פתוחים · מקדמות · קלסרים · מסמכים
  - Each tile: icon + title + primary metric + secondary detail
  - TailwindCSS only — no new dependencies
- [x] Add `ClientStatusCard` as first section in client detail page

---

## Feature 5 — Timeline: Tax Events

### Backend
- [x] Extend `app/timeline/services/timeline_service.py`
  - Import `TaxDeadline` and `AnnualReport` models (service-level only, no repo-layer cross-domain)
  - Add `_build_tax_deadline_events(client_id)` → event_type `"tax_deadline_due"`, description = deadline type + due date + amount, metadata includes `tax_deadline_id`
  - Add `_build_annual_report_events(client_id)` → event_type `"annual_report_status_changed"`, description = form type + status + year, metadata includes `annual_report_id`
  - Merge both event lists into main timeline, maintain sort by timestamp desc
  - Both event types: `actions = []`

### Frontend
- [x] In `src/features/timeline/` add Hebrew label + icon for `"tax_deadline_due"`
  - Label: "מועד מס" · icon: `CalendarClock` (lucide-react)
- [x] In `src/features/timeline/` add Hebrew label + icon for `"annual_report_status_changed"`
  - Label: "דוח שנתי" · icon: `FileText` (lucide-react)
- [x] In `src/features/taxDeadlines/hooks/` — add timeline invalidation on create/complete mutations
  - `queryClient.invalidateQueries({ queryKey: QK.clients.timeline(clientId) })`
- [x] In `src/features/annualReports/hooks/` — add timeline invalidation on status transition mutations

---

## Feature 6 — Document Delete / Replace

### Backend
- [x] Add `is_deleted` boolean column (default `False`) to `PermanentDocument` ORM model
- [x] Update `GET /api/v1/documents/client/{client_id}` to filter `is_deleted = False`
- [x] Add `delete_document(document_id, requesting_user)` to `app/permanent_documents/services/`
  - Set `is_deleted = True` (soft delete — no filesystem removal in this sprint)
  - Raise 404 if not found
- [x] Add `replace_document(document_id, file, requesting_user)` to service
  - Accept new file upload
  - Overwrite `storage_key`, reset `uploaded_at`, keep `is_present = True`
  - Raise 404 if not found or is_deleted
- [x] Add routes to `app/permanent_documents/api/`
  - `DELETE /api/v1/documents/{document_id}` — ADVISOR only → 204
  - `PUT /api/v1/documents/{document_id}/replace` — ADVISOR only, multipart upload → 200 + updated document

### Frontend
- [x] Add `ENDPOINTS.documentById(id)` and `ENDPOINTS.documentReplace(id)` in `src/api/endpoints.ts`
- [x] Add `documentsApi.deleteDocument(id)` in `src/api/documents.api.ts`
- [x] Add `documentsApi.replaceDocument(id, file)` in `src/api/documents.api.ts`
- [x] In `DocumentsDataCards.tsx`, add per-row actions (ADVISOR only):
  - "מחק" button (`Trash2` icon) — show confirmation dialog before calling delete
  - "החלף" button (`RefreshCw` icon) — open hidden file input, upload on file selection
  - On delete success: `toast.success("מסמך נמחק")`, invalidate documents query
  - On replace success: `toast.success("מסמך הוחלף")`, invalidate documents query

---

## Feature 7 — Fix In-Memory Pagination

### Backend — Advance Payments
- [x] Update `app/advance_payments/repositories/` `list_by_client_year`
  - Add `page: int = 1`, `page_size: int = 50` parameters
  - Run `SELECT COUNT(*)` before applying `LIMIT` / `OFFSET`
  - Return `{ items, total, page, page_size }`
- [x] Update `app/advance_payments/schemas/` — add `AdvancePaymentListResponse` (PaginatedResponse pattern)
- [x] Update `app/advance_payments/services/` to pass pagination params and return paginated schema
- [x] Update `app/advance_payments/api/` — accept `page` / `page_size` query params, return new schema

### Backend — Authority Contacts
- [x] Update `app/authority_contact/repositories/` `list_by_client`
  - Add `page: int = 1`, `page_size: int = 50` parameters
  - Run `SELECT COUNT(*)` before applying `LIMIT` / `OFFSET`
  - Return `{ items, total, page, page_size }`
- [x] Update `app/authority_contact/schemas/` — add `AuthorityContactListResponse`
- [x] Update `app/authority_contact/services/` and `app/authority_contact/api/` accordingly

### Frontend
- [x] Check `src/features/advancePayments/` — if currently reading flat array, update to read `.items`
- [x] Check `src/features/authorityContacts/` — if currently reading flat array, update to read `.items`
- [x] Update any TypeScript response types for both domains to match paginated shape

---

## Cross-Cutting Checklist

Apply to every feature before marking it done:

- [ ] No Python file exceeds 150 lines — split if needed
- [ ] No raw SQL anywhere — ORM only
- [ ] Layer order respected: API → Service → Repository (no skipping)
- [ ] New endpoint registered in `src/api/endpoints.ts`
- [ ] New query key registered in `src/lib/queryKeys.ts`
- [ ] React Query options: `staleTime: 30_000`, `retry: 1`
- [ ] All UI text is Hebrew — zero English visible to user
- [ ] Role enforcement: `require_role()` on backend, `useAuthStore()` on frontend
- [ ] `npm run typecheck` passes with zero errors
- [ ] `npm run lint` passes with zero warnings
- [ ] Backend tests pass: `JWT_SECRET=test-secret pytest -q`

---

## Dependency Order

```
Feature 7  (no deps)     ← safe to start first, unblocks nothing but cleans debt
Feature 1  (no deps)     ← required before Feature 4
Feature 2  (needs F1)
Feature 3  (no deps)     ← can run in parallel with F1/F2
Feature 4  (needs F1)
Feature 5  (no deps)     ← can run in parallel with everything
Feature 6  (no deps)     ← can run in parallel with everything
```
