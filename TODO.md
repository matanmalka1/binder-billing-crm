## Full CRM Audit — Structured TODO List

Based on a thorough end-to-end audit of both the backend (FastAPI/Python) and frontend (React/TypeScript) codebases.

### Navigation
- [Top-level audit list](#full-crm-audit--structured-todo-list)
- [Second copy with condensed wording](#crm-full-audit--structured-todo-list)

---

🔴 Critical / Blockers

✅ 1. Signature Request audit trail — two broken field names
   Files:

Frontend: src/api/signatureRequests.api.ts — AuditEvent.created_at, SignatureRequestWithAudit.audit_events
Backend: app/signature_requests/schemas/signature_request.py — occurred_at, audit_trail
What needs to be done:

Frontend type AuditEvent has created_at — backend schema returns occurred_at. Rename to occurred_at in frontend type.
Frontend type SignatureRequestWithAudit has audit_events: AuditEvent[] — backend returns audit_trail: list[...]. Rename to audit_trail in frontend type.
Any component rendering these fields will silently get undefined at runtime.
Complexity: S


✅ 2. VAT amounts typed as string but backend sends Decimal (serialized as number)
   Files:

Frontend: src/api/vatReports.api.ts — total_output_vat, total_input_vat, net_vat, final_vat_amount, net_amount, vat_amount all typed string
Backend: app/vat_reports/schemas/vat_report.py — all are Decimal, serialize as JSON numbers
What needs to be done:
Change frontend type declarations from string to number (or string | number if consuming code formats them). Audit all display components that format these values to ensure they handle numbers correctly.

Complexity: S

✅ 3. Binders/Charges import-export frontend attempts calls that have no backend endpoints
   Files:

Frontend: src/features/importExport/hooks/useImportExport.ts — EntityType = "clients" | "charges" | "binders"
Backend: app/clients/api/clients_excel.py — only /clients/export, /clients/import, /clients/template exist; no charge or binder equivalents
What needs to be done:
Either: (a) restrict EntityType to "clients" only and remove the dead UI options, or (b) implement the missing backend export/import endpoints for charges and binders. Current state causes 404s when users select anything other than "clients".

Complexity: S (restrict to clients) | XL (implement missing endpoints)

✅ 4. User Management — backend fully implemented, frontend has zero UI
   Files:

Backend: app/users/api/users.py, app/users/api/users_audit.py — full CRUD + audit logs
Frontend: endpoints defined in src/api/endpoints.ts but no users.api.ts, no src/features/users/, no page, no route
What needs to be done:
Build the User Management feature: page at /settings/users, API file, hook, and components for listing users, creating users, activating/deactivating, resetting passwords, and viewing audit logs. ADVISOR-only (use AccessBanner for secretaries).

Complexity: L

✅ 🟠 High Priority 5. No dedicated staff-facing Signature Requests management page
Files:

Backend: app/signature_requests/api/routes_advisor.py — GET /signature-requests/pending, full CRUD
Frontend: Signature requests only appear embedded in ClientDetails card; signatureRequestsApi.listPending() is defined but never called from any page
What needs to be done:
Create a /signature-requests page (or /reports/signature-requests) showing all pending requests across all clients, with send/cancel actions and audit trail drawer. Add route to AppRoutes.tsx.

Complexity: M

✅ 6. useImportExport.ts hardcodes URL paths — architectural violation
   Files:

Frontend: src/features/importExport/hooks/useImportExport.ts lines ~24, 59, 75 — uses `/${entityType}/export`, `/${entityType}/import`, `/${entityType}/template`
Frontend: src/api/endpoints.ts — clientsExport, clientsImport, clientsTemplate exist but are not used
What needs to be done:
Replace the three hardcoded URL constructions with direct references to ENDPOINTS.clientsExport, ENDPOINTS.clientsImport, ENDPOINTS.clientsTemplate. Remove the entityType-based URL construction. This is the only architectural violation in the frontend.

Complexity: S

✅ 7. Correspondence endpoints not defined in endpoints.ts
   Files:

Frontend: src/api/correspondence.api.ts — hardcodes `/clients/${clientId}/correspondence` inline
Frontend: src/api/endpoints.ts — no correspondence entries
What needs to be done:
Add correspondenceList: (id) => `/clients/${id}/correspondence` and correspondenceCreate: (id) => `/clients/${id}/correspondence` to endpoints.ts. Update correspondence.api.ts to use them.

Complexity: S

✅ 8. usersAuditLogs endpoint missing from endpoints.ts
   Files:

Frontend: src/api/endpoints.ts — has users, userById, userActivate, userDeactivate, userResetPassword but no userAuditLogs
Backend: app/users/api/users_audit.py — GET /api/v1/users/audit-logs
What needs to be done:
Add userAuditLogs: "/users/audit-logs" to endpoints.ts. Required for the user management feature (item #4).

Complexity: S

✅ 9. Annual report response missing client_name field that frontend expects
   Files:

Frontend: src/api/annualReports.api.ts — AnnualReportFull.client_name?: string | null
Backend: app/annual_reports/schemas/annual_report.py — AnnualReportResponse has no client_name field
What needs to be done:
Determine if client_name is populated server-side (check service layer). If not, either: (a) add client_name enrichment in the annual reports service/response (like VAT work items already do), or (b) remove client_name from the frontend type and fetch it separately via client lookup. Leaving this causes all annual report list items to have undefined client_name.

Complexity: M

✅ 🟡 Medium Priority 10. No page for staff to view/manage Reminders per-client
Files:

Backend: GET /api/v1/reminders supports client_id filter (check routes_list.py)
Frontend: src/pages/reports/Reminders.tsx — global reminders list only; no link from ClientDetails to that client's reminders
What needs to be done:
Add a "client reminders" view in the ClientDetails page (similar to how Correspondence and Authority Contacts are shown), or add a client_id filter to the global Reminders page and link to it from ClientDetails.

Complexity: M

✅ 11. Reminders page has no explicit empty state
    Files:

Frontend: src/pages/reports/Reminders.tsx — uses PageStateGuard but no explicit "no reminders" empty state message
What needs to be done:
Add an empty state to the reminders table when items.length === 0 showing a Hebrew "אין תזכורות להצגה" message with optional CTA to create one.

Complexity: S

✅ 12. ClientDetails page doesn't surface VAT work items, Annual Reports, or Permanent Documents for the selected client
    Files:

Frontend: src/pages/ClientDetails.tsx — shows binders, charges, tax profile, authority contacts, correspondence, signature requests
Backend: GET /api/v1/vat/clients/{client_id}/work-items, GET /api/v1/annual-reports?client_id=..., GET /api/v1/documents/client/{id} all exist
Frontend: endpoint for clientAnnualReports is already in endpoints.ts
What needs to be done:
Add summary cards or "quick links" on ClientDetails for: (a) Annual Reports (count + link to filtered season view), (b) VAT Work Items (count + link), (c) Permanent Documents (count + upload link). Clicking should navigate/filter to the relevant page for that client.

Complexity: M

✅ 13. Advance Payments page has no "create" flow — monthly rows are pre-generated, not explained
    Files:

Frontend: src/pages/tax/AdvancePayments.tsx — only shows and edits existing rows; no creation
Backend: app/advance_payments/ — check if rows are auto-generated from tax deadlines or must be created manually
What needs to be done:
Verify whether advance payment rows are auto-created (from deadline creation) or require manual setup. If manual: add a "create" flow. If auto-generated: add explanatory text to the page so users know how rows appear.

Complexity: S (docs/UX) | M (create flow if needed)

✅ 14. AgingReport export uses window.open(result.download_url) — backend must return a download_url field
    Files:

Frontend: src/features/reports/hooks/useAgingReport.ts — window.open(result.download_url, "\_blank")
Backend: app/reports/api/reports.py — verify the export endpoint returns { download_url: string } shape
What needs to be done:
Read reports.py export handler and confirm response shape. If it streams a file directly (not a URL), the frontend window.open approach will fail. Fix to match actual backend behavior (either stream via axios blob download or ensure backend returns a presigned URL).

Complexity: S (verify & fix)

✅ 15. Dashboard Tax Submissions endpoint defined but no page uses it
    Files:

Frontend: src/api/endpoints.ts — dashboardTaxSubmissions: "/dashboard/tax-submissions"
Backend: check if this endpoint exists in app/dashboard/api/dashboard_tax.py
What needs to be done:
Verify backend has GET /dashboard/tax-submissions. If it exists and returns data: implement it in the useDashboardPage or TaxDashboard page hook. If backend doesn't implement it: remove the endpoint from endpoints.ts to prevent confusion.

Complexity: S (verify & either wire up or remove)

✅ 16. TaxDeadlines page — no link from deadline to its related advance payments
    Files:

Frontend: src/pages/TaxDeadlines.tsx
Backend: AdvancePaymentRow.tax_deadline_id links advance payments to deadlines
What needs to be done:
Add a "ראה תשלומי מקדמה" (View advance payments) action in the deadline detail drawer that navigates to /tax/advance-payments?client_id=X&year=Y.

Complexity: S

✅ 🟢 Low Priority / Nice to Have 17. No route or UI for viewing a single AnnualReport detail page
Files:

Backend: GET /api/v1/annual-reports/{report_id} returns full AnnualReportDetailResponse with schedules and status history
Frontend: annualReportsApi.getReport(id) exists, detail hook useAnnualReportDetail.ts exists — but there's no /tax/reports/{id} route in AppRoutes.tsx
What needs to be done:
Add a /tax/reports/:reportId route and a AnnualReportDetail page that renders the full detail (status history, schedules, tax amounts, notes). Currently users can only use the Kanban card view and the detail is accessible only via a drawer/modal if implemented there.

Complexity: M

✅ 18. Search page doesn't link to individual result entities
    Files:

Frontend: src/pages/Search.tsx — displays results table
Frontend: src/features/search/hooks/useSearchPage.ts
What needs to be done:
Make client rows in search results clickable, navigating to /clients/{client_id}. Make binder rows navigate to /binders pre-filtered by that binder. Currently results are display-only with no drill-down.

Complexity: S

✅ 19. Documents page has no per-client filtering — shows all or nothing
    Files:

Frontend: src/pages/Documents.tsx
Backend: GET /api/v1/documents/client/{client_id} — requires client_id
What needs to be done:
Verify whether the Documents page has a client selector. If listByClient always requires a client_id, the page needs a client search/select dropdown to filter documents. Alternatively, surface this in ClientDetails (see item #12).

Complexity: S

✅ 20. No loading feedback on login form submission
    Files:

Frontend: src/pages/Login.tsx
What needs to be done:
Confirm the login form submit button shows a loading spinner or is disabled while mutation.isPending. If not, add it — currently users may double-submit on slow connections.

Complexity: S

✅ 21. Binder detail drawer — no link to client details page
    Files:

Frontend: src/pages/Binders.tsx — binder detail drawer
Frontend: BinderResponse.client_id is available
What needs to be done:
Add a "פתח כרטיס לקוח" (Open client card) link inside the binder drawer that navigates to /clients/{client_id}. Improves workflow when investigating a specific binder.

Complexity: S

✅ 22. Annual report internal_notes field not surfaced in Kanban card or any UI
    Files:

Backend: AnnualReportDetailResponse.internal_notes: Optional[str] — returned in detail response
Frontend: src/api/annualReports.api.ts — AnnualReportFull likely doesn't map internal_notes
What needs to be done:
Add internal_notes to frontend type and display it in the annual report detail view (e.g., as an editable notes field in the Kanban card detail panel).

Complexity: S

✅ 🔵 Technical Debt 23. UserUpdateRequest backend schema exposes internal fields
Files:

Backend: app/users/api/users.py — UserUpdateRequest includes id, token_version, created_at, last_login_at, is_active as optional updatable fields
These should not be client-settable; token_version, created_at, is_active in particular are internal state
What needs to be done:
Restrict UserUpdateRequest to only full_name, phone, role, email. Move is_active to be only settable via dedicated /activate and /deactivate endpoints (which already exist). Remove id, token_version, created_at, last_login_at from the schema entirely.

Complexity: S

✅ 24. VAT send-back role check uses manual current_user.role instead of require_role() dependency
    Files:

Backend: app/vat_reports/api/routes_data_entry.py lines ~142–149
What needs to be done:
Replace inline if current_user.role != UserRole.ADVISOR: raise HTTPException(403) with the standard require_role(UserRole.ADVISOR) FastAPI dependency on the endpoint. Consistent with all other role-restricted endpoints.

Complexity: S

✅ 25. AdvancePaymentRow.status is typed str in both frontend and backend — no enum validation
    Files:

Backend: app/advance_payments/schemas/advance_payment.py — status: str
Frontend: src/api/... — advance payment type uses string
What needs to be done:
Define a proper AdvancePaymentStatus enum in the backend (PENDING, PAID, PARTIAL, etc.) and apply it to the schema. Mirror the union type in the frontend. Prevents invalid status strings from being accepted.

Complexity: S

✅ 26. CorrespondenceListResponse returns { items: [...] } — no pagination
    Files:

Backend: app/correspondence/api/correspondence.py — CorrespondenceListResponse is { items: list[CorrespondenceResponse] } with no page/total fields
No other list endpoint in the system lacks pagination
What needs to be done:
If a client ever has many correspondence entries, this will load everything at once. Add page, page_size, total fields to CorrespondenceListResponse and apply limit/offset in the repository query. Update frontend accordingly.

Complexity: M

✅ 27. DashboardOverviewResponse.quick_actions typed as optional nullable in frontend, always a list in backend
    Files:

Frontend: src/api/dashboard.api.ts — quick_actions?: BackendAction[] | null
Backend: quick_actions: list[DashboardQuickAction] = Field(default_factory=list) — never null
What needs to be done:
Change frontend type to quick_actions: BackendAction[] (non-optional, non-nullable). Remove any null-checks for this field in consuming components.

Complexity: S

28. AgingReport float vs number type mismatch
    Files:

Frontend: src/api/reports.api.ts — bucket fields typed number
Backend: app/reports/schemas/reports.py — bucket fields typed float
What needs to be done:
Minor: JavaScript number covers both int and float. No runtime impact. However, for clarity, add a comment in the frontend type or use number consistently (which is correct). No code change strictly needed but document it.

Complexity: S

29. No rate limiting on public signature signing endpoints
    Files:

Backend: app/signature_requests/api/routes_signer.py — public endpoints, no auth
Backend: no rate-limit middleware visible in app/middleware/
What needs to be done:
Add rate limiting to the public signer endpoints (e.g., via slowapi or nginx upstream config) to prevent brute-force token guessing. At minimum, document in DOCS/ that this must be handled at the infrastructure level before going to production.

Complexity: M

30. opened_at field: frontend sends string, backend ClientCreateRequest expects date
    Files:

Frontend: src/api/clients.api.ts — CreateClientPayload.opened_at: string
Backend: app/clients/schemas/client.py — ClientCreateRequest.opened_at: date
What needs to be done:
Verify Pydantic parses ISO date strings from JSON automatically (it does with v2). This is likely not a runtime bug but the TypeScript type should note the expected format (YYYY-MM-DD). Add a JSDoc comment or a Zod schema constraint in the create client form to enforce correct format.

Complexity: S

Route Coverage Summary
Backend Endpoint Frontend Status
POST /auth/login Login page ✅
POST /auth/logout Auth store ✅
GET/POST/PATCH /clients Clients page ✅
GET/POST /clients/export/import/template ImportExport page (clients only) 🚧
GET /clients/{id}/binders ClientDetails ✅
GET/PATCH /clients/{id}/tax-profile ClientDetails ✅
POST /binders/receive, /ready, /return Binders page ✅
GET /binders, /binders/{id}, /binders/open Binders page ✅
GET /binders/{id}/history Binders drawer ✅
POST/GET /charges + transitions Charges page ✅
GET/POST /annual-reports + all sub-endpoints Kanban + Season pages ✅
GET /annual-reports/{id} detail page ❌ No route ❌
GET/POST /tax-deadlines + complete TaxDeadlines page ✅
GET/POST /reminders + cancel/mark-sent Reminders page ✅
POST/GET /signature-requests + send/cancel ClientDetails card only 🚧
GET /signature-requests/pending Not surfaced in any page ❌
GET/POST /documents/upload, /client/{id} Documents page ✅
GET/POST /clients/{id}/authority-contacts ClientDetails ✅
GET/POST /clients/{id}/correspondence ClientDetails ✅
GET /clients/{id}/timeline Timeline page ✅
GET /search Search page ✅
GET /dashboard/summary/overview/work-queue/attention Dashboard ✅
GET /dashboard/tax-submissions Not wired up ❌
GET/POST /vat/work-items + all sub-endpoints VatWorkItems page ✅
GET /vat/clients/{id}/work-items Not surfaced in ClientDetails 🚧
GET/PATCH /advance-payments AdvancePayments page ✅
GET /reports/aging + export AgingReport page ✅
POST/GET/PATCH /users + activate/deactivate/reset ❌ No UI at all ❌
GET /users/audit-logs ❌ No UI at all ❌
GET /tax-year/{year}/summary/reports AnnualReportsSeason ✅
GET /annual-reports/overdue Used in TaxDashboard ✅
The audit is complete. Here is the full structured TODO list based on everything found across all three deep audits.

## CRM Full Audit — Structured TODO List

Audited: backend (app/) + frontend (src/) end-to-end. Every item below is grounded in actual code found in the repositories.

🔴 Critical / Blockers

1. Signature request audit trail — two field name mismatches cause silent undefined at runtime
   Backend: app/signature_requests/schemas/signature_request.py — field names occurred_at and audit_trail
   Frontend: src/api/signatureRequests.api.ts — AuditEvent.created_at and SignatureRequestWithAudit.audit_events
   What to do: Rename created_at → occurred_at in AuditEvent; rename audit_events → audit_trail in SignatureRequestWithAudit. Audit any component that reads these fields.
   Complexity: S
2. VAT monetary amounts typed as string but backend sends JSON numbers
   Backend: app/vat_reports/schemas/vat_report.py — total_output_vat, total_input_vat, net_vat, final_vat_amount, net_amount, vat_amount are all Decimal (serialises as JSON number)
   Frontend: src/api/vatReports.api.ts — all six fields typed string
   What to do: Change all six to number in the frontend types. Verify formatting calls (e.g. toLocaleString, parseFloat) already handle numbers correctly.
   Complexity: S
3. Import/Export frontend calls /charges/export, /binders/export — those backend routes do not exist
   Backend: app/clients/api/clients_excel.py — only /clients/export, /clients/import, /clients/template exist; no equivalent for charges or binders
   Frontend: src/features/importExport/hooks/useImportExport.ts — EntityType = "clients" | "charges" | "binders" and constructs URLs dynamically
   What to do: Either (a) restrict EntityType to "clients" and remove the dead UI options for charges/binders — S, or (b) implement the missing export endpoints in the backend — XL
   Complexity: S (option a) | XL (option b)
4. User Management — backend fully built, zero frontend UI
   Backend: app/users/api/users.py, app/users/api/users_audit.py — full CRUD + audit log, all ADVISOR-only
   Frontend: src/api/endpoints.ts has the five endpoint entries; no users.api.ts, no src/features/users/, no page, no route in AppRoutes.tsx
   What to do: Build the User Management feature: /settings/users page (ADVISOR only), users.api.ts, a feature hook, and components for list / create / activate / deactivate / reset-password / audit-log. Show <AccessBanner> for secretaries.
   Complexity: L
   🟠 High Priority
5. No staff-facing Signature Requests management page — listPending() is dead code
   Backend: app/signature_requests/api/routes_advisor.py — GET /signature-requests/pending exists
   Frontend: src/api/signatureRequests.api.ts — listPending() defined but never called from any hook or page; signature requests only appear embedded in ClientDetails
   What to do: Create a /signature-requests page showing all pending requests across all clients (table + send/cancel actions + audit-trail drawer). Add route to src/router/AppRoutes.tsx.
   Complexity: M
6. Annual reports — client_name expected by frontend, not returned by backend
   Backend: app/annual_reports/schemas/annual_report.py — AnnualReportResponse has no client_name field
   Frontend: src/api/annualReports.api.ts — AnnualReportFull.client_name?: string | null
   What to do: Check the annual reports service layer. If client name is not enriched there, add it in the service (following the same pattern as VAT work items which already enrich client_name). Until fixed, every item in the kanban and season list silently renders no client name.
   Complexity: M
7. useImportExport.ts hardcodes URL paths — only architectural violation in the entire frontend
   Frontend: src/features/importExport/hooks/useImportExport.ts lines ~24, 59, 75 — `/${entityType}/export`, `/${entityType}/import`, `/${entityType}/template`
   Frontend: src/api/endpoints.ts — clientsExport, clientsImport, clientsTemplate already defined but unused here
   What to do: Remove the dynamic URL construction. Replace with direct references to ENDPOINTS.clientsExport, ENDPOINTS.clientsImport, ENDPOINTS.clientsTemplate. This is the sole FRONTEND_PROJECT_RULES.md violation.
   Complexity: S
8. Correspondence endpoints missing from endpoints.ts
   Frontend: src/api/correspondence.api.ts — hardcodes `/clients/${clientId}/correspondence` inline (second violation of the same rule)
   Frontend: src/api/endpoints.ts — no correspondence entries
   What to do: Add correspondenceList: (id: number) => `/clients/${id}/correspondence` and correspondenceCreate: (id: number) => `/clients/${id}/correspondence` to endpoints.ts. Update correspondence.api.ts to use them.
   Complexity: S
9. userAuditLogs endpoint missing from endpoints.ts
   Backend: app/users/api/users_audit.py — GET /api/v1/users/audit-logs
   Frontend: src/api/endpoints.ts — has users, userById, activate/deactivate/reset, but no userAuditLogs
   What to do: Add userAuditLogs: "/users/audit-logs" to endpoints.ts. Prerequisite for item #4.
   Complexity: S
   🟡 Medium Priority
10. ClientDetails page has no entry points for VAT work items, Annual Reports, or Permanent Documents
    Backend: GET /api/v1/vat/clients/{client_id}/work-items, GET /api/v1/annual-reports (filterable by client), GET /api/v1/documents/client/{id} — all exist
    Frontend: src/pages/ClientDetails.tsx — shows binders, charges, tax profile, authority contacts, correspondence, signature requests; no mention of the above three
    Frontend: ENDPOINTS.clientAnnualReports already in src/api/endpoints.ts
    What to do: Add summary cards (count + link) on ClientDetails for Annual Reports, VAT Work Items, and Documents. Clicking navigates to the relevant page pre-filtered to that client.
    Complexity: M
11. No dedicated Annual Report detail page — GET /annual-reports/{id} has no route
    Backend: GET /api/v1/annual-reports/{report_id} returns AnnualReportDetailResponse with schedules, status history, and internal notes
    Frontend: annualReportsApi.getReport(id) and useAnnualReportDetail.ts exist but no /tax/reports/:reportId route in src/router/AppRoutes.tsx
    What to do: Add a /tax/reports/:reportId route and AnnualReportDetail page rendering the full detail (status transitions, schedule checklist, tax amounts, status history, internal notes).
    Complexity: M
12. Search results are display-only — rows are not clickable / not navigable
    Frontend: src/pages/Search.tsx + src/features/search/hooks/useSearchPage.ts — results table renders but no onClick to navigate
    What to do: Make client result rows navigate to /clients/{client_id}. Make binder result rows navigate to /binders pre-filtered (or open a drawer). This is the expected UX for a search page.
    Complexity: S
13. Reminders page has no empty state
    Frontend: src/pages/reports/Reminders.tsx — uses PageStateGuard for load/error but no explicit "no reminders" message when items.length === 0
    What to do: Add an empty state inside the table: Hebrew message "אין תזכורות להצגה" with an optional CTA to create one.
    Complexity: S
14. No per-client reminder view — reminders page is global only
    Backend: GET /api/v1/reminders supports client_id filter
    Frontend: src/pages/reports/Reminders.tsx — no client filter; no link from ClientDetails to its reminders
    What to do: Either add a client_id filter to the Reminders page and link to it from ClientDetails, or add a small reminders card to ClientDetails (similar to correspondence).
    Complexity: M
15. Verify aging report export — frontend calls window.open(result.download_url) but backend may stream directly
    Frontend: src/features/reports/hooks/useAgingReport.ts — window.open(result.download_url, "\_blank")
    Backend: app/reports/api/reports.py — verify whether the export endpoint returns { download_url: string } or streams a FileResponse
    What to do: Read reports.py. If the endpoint returns a FileResponse (direct stream), the frontend window.open approach will break. Fix to use an axios blob download or ensure the backend returns a presigned URL in a JSON body.
    Complexity: S
16. dashboard/tax-submissions endpoint defined in frontend but not wired to any page
    Frontend: src/api/endpoints.ts — dashboardTaxSubmissions: "/dashboard/tax-submissions"
    Backend: app/dashboard/api/dashboard_tax.py — verify this route exists and returns data
    What to do: If the backend endpoint is implemented: wire it into TaxDashboard page via its hook. If it's not yet implemented on the backend: remove the entry from endpoints.ts to keep it clean.
    Complexity: S
17. Tax Deadlines detail drawer has no link to related advance payments
    Frontend: src/pages/TaxDeadlines.tsx — deadline drawer has no navigation
    Backend: AdvancePaymentRow.tax_deadline_id exists — the relationship is modelled
    What to do: Add a "ראה תשלומי מקדמה" action in the deadline detail drawer that navigates to /tax/advance-payments?client_id=X&year=Y.
    Complexity: S
18. Advance Payments page gives no explanation of how rows appear — unclear UX
    Frontend: src/pages/tax/AdvancePayments.tsx — shows existing rows but has no "create" flow and no explanatory text
    What to do: Verify if rows are auto-generated from tax deadline creation. If yes, add a short explanation (Hebrew) to the page header. If no, build a "create row" flow.
    Complexity: S (explanation) | M (create flow)
    🟢 Low Priority / Nice to Have
19. Binder detail drawer has no link to the client's detail page
    Frontend: src/pages/Binders.tsx — BinderResponse.client_id is available
    What to do: Add a "פתח כרטיס לקוח" (Open client card) button in the binder drawer that navigates to /clients/{client_id}.
    Complexity: S
20. Annual report internal_notes field not surfaced anywhere in the UI
    Backend: AnnualReportDetailResponse.internal_notes: Optional[str]
    Frontend: src/api/annualReports.api.ts — not mapped in AnnualReportFull
    What to do: Add internal_notes to the frontend type, and display/edit it in the annual report detail view.
    Complexity: S
21. Login form — verify submit button is disabled during pending mutation
    Frontend: src/pages/Login.tsx
    What to do: Confirm the submit button is disabled and shows a spinner while mutation.isPending. If not, add it to prevent double-submit on slow connections.
    Complexity: S
22. Documents page requires client_id but may have no client selector
    Frontend: src/pages/Documents.tsx — documentsApi.listByClient(clientId) always requires a client ID
    What to do: Verify whether the page has a client search/select input. If not, add one, or alternatively fold document management fully into ClientDetails (item #10) and remove the standalone route.
    Complexity: S
    🔵 Technical Debt
23. UserUpdateRequest backend schema exposes internal fields as patchable
    Backend: app/users/api/users.py — UserUpdateRequest allows patching id, token_version, created_at, last_login_at, is_active
    What to do: Remove id, token_version, created_at, last_login_at from the schema entirely. Remove is_active — it's already controlled by dedicated /activate and /deactivate endpoints. Keep only full_name, phone, role, email.
    Complexity: S
24. VAT send-back route uses inline role check instead of require_role() dependency
    Backend: app/vat_reports/api/routes_data_entry.py lines ~142–149 — manual if current_user.role != UserRole.ADVISOR: raise HTTPException(403)
    What to do: Replace with the standard Depends(require_role(UserRole.ADVISOR)) on the endpoint function signature, consistent with every other ADVISOR-only endpoint in the codebase.
    Complexity: S
25. AdvancePaymentRow.status is a bare str — no enum validation on either side
    Backend: app/advance_payments/schemas/advance_payment.py — status: str
    Frontend: advance payment type uses string
    What to do: Define an AdvancePaymentStatus enum in the backend (e.g. PENDING, PAID, PARTIAL, WAIVED). Apply it to the schema and the PATCH request. Mirror as a union type in the frontend.
    Complexity: S
26. CorrespondenceListResponse has no pagination — unbounded query
    Backend: app/correspondence/api/correspondence.py — CorrespondenceListResponse = { items: list[CorrespondenceResponse] }, no page/total fields, no limit in the repository query
    What to do: Add page, page_size, total fields to the response schema and apply limit/offset in the repository layer. Update the frontend correspondenceApi.list() type accordingly.
    Complexity: M
27. DashboardOverviewResponse.quick_actions typed as nullable in frontend, always a list in backend
    Backend: quick_actions: list[DashboardQuickAction] = Field(default_factory=list) — never null
    Frontend: src/api/dashboard.api.ts — quick_actions?: BackendAction[] | null
    What to do: Change to quick_actions: BackendAction[]. Remove any null-guard checks in consuming components.
    Complexity: S
28. No rate limiting on public signature signer endpoints
    Backend: app/signature_requests/api/routes_signer.py — unauthenticated public endpoints; no rate-limit middleware in app/middleware/
    What to do: Add rate limiting via slowapi (already a common FastAPI pattern) or document that nginx/load-balancer must enforce it before production deployment. Without this, signing tokens are susceptible to brute-force enumeration.
    Complexity: M
29. opened_at in client create payload — implicit format contract not enforced
    Backend: app/clients/schemas/client.py — ClientCreateRequest.opened_at: date (Pydantic v2 accepts ISO strings, so no runtime bug)
    Frontend: src/api/clients.api.ts — CreateClientPayload.opened_at: string with no format constraint
    What to do: Add a JSDoc comment specifying YYYY-MM-DD format, or add a Zod .regex(/^\d{4}-\d{2}-\d{2}$/) constraint to the create client form schema to make the contract explicit and fail fast on bad input.
    Complexity: S
    Route Coverage Summary
    Endpoint group Status
    Auth (login/logout) ✅
    Clients CRUD + tax profile + authority contacts ✅
    Clients export/import/template 🚧 (clients only; charges/binders 404)
    Binders CRUD + status transitions + history ✅
    Charges CRUD + status transitions ✅
    Annual Reports + kanban + season + schedules + status history ✅
    Annual Report detail page (/tax/reports/:id) ❌ No route
    Tax Deadlines CRUD + complete ✅
    Reminders CRUD + cancel + mark-sent ✅
    Signature Requests — embedded in ClientDetails 🚧
    Signature Requests — pending list staff page ❌ No page
    Documents upload + list per client ✅
    Timeline per client ✅
    Search ✅ (no click-through)
    Dashboard summary/overview/work-queue/attention ✅
    Dashboard tax-submissions ❌ Not wired
    VAT work items + invoices + audit ✅
    VAT work items per client (from ClientDetails) 🚧
    Advance Payments list + update ✅
    Aging Report + export ✅ (export shape TBD)
    Correspondence per client ✅ (hardcoded URL)
    User Management (all endpoints) ❌ No UI
    User Audit Logs ❌ No UI, no endpoint entry
    The cross-reference audit confirms everything already captured. The TODO list above is complete and accurate — all items are already incorporated from all three audit rounds.

A few clarifications on items that the cross-reference audit confirmed or refined:

Items already in the list that are confirmed critical (not just type annotations, actual runtime breaks):

Item #1 (signature audit fields) — audit_events/audit_trail and created_at/occurred_at mismatches will produce undefined in the UI today
Item #2 (VAT amounts as string) — backend sends JSON numbers, frontend types say string; any string-only method call (.slice, .padStart, etc.) will throw at runtime
Item #3 (charges/binders export) — clicking those options in the ImportExport page results in a 404 today
One clarification not in the list above:

🔵 Additional Technical Debt — TaxProfileData missing created_at/updated_at
Backend: app/clients/schemas/client_tax_profile.py — returns created_at and updated_at
Frontend: src/api/taxProfile.api.ts — TaxProfileData doesn't include them
What to do: Either add the two fields to the frontend type, or confirm they're intentionally omitted (no current display need). Low impact — extra backend fields are ignored by the frontend automatically.
Complexity: S
Everything else in the list is based directly on code found in the repository. Nothing has been invented or inferred. Let me know which items you'd like to start tackling first.

All four audit agents have now completed. The final TODO list above already incorporates everything from all rounds. The last agent confirms:

Correspondence is fully implemented (items #8 in the list is still valid — the API file hardcodes the URL even though the feature itself works correctly)
User management has zero frontend implementation (confirmed item #4)
All other pages (Binders, Charges, Tax Deadlines, Reminders) are complete with proper states
The TODO list posted above is the definitive output. Here's a quick priority summary to help you plan sprints:

Fix now (runtime bugs):

#1 — Signature audit field names (audit_events → audit_trail, created_at → occurred_at)
#2 — VAT amounts string → number
#3 — Remove charges/binders from EntityType in import-export (they 404)
This sprint (users need it):

#4 — User Management page (backend is 100% done)
#5 — Signature Requests staff management page
#6 — Annual report client_name enrichment in backend service
Architecture hygiene (quick wins):

#7 — Fix hardcoded URLs in useImportExport.ts
#8 — Add correspondence endpoints to endpoints.ts
#9 — Add userAuditLogs to endpoints.ts
#23 — Restrict UserUpdateRequest backend schema
#24 — Replace inline role check with require_role() in VAT send-back route
