
## [P2] 2.8 — חישוב חי (Live Calculation)
**Status:** PARTIAL
**Gap:** Tax calculation is on-demand via REST; no WebSocket/SSE endpoint for real-time recalculation as fields change.
**Files to touch:**
- `app/annual_reports/api/annual_report_financials.py` — add `GET /annual-reports/{id}/tax-calculation/stream` SSE endpoint
**Acceptance criteria:** SSE endpoint emits updated `TaxCalculationResponse` whenever the client sends a field-change signal, without full page reload.

---

## [P2] 1.9 — הגשה לרשות (Submission to Tax Authority)
**Status:** PARTIAL
**Gap:** Endpoint changes status and saves `ita_reference` manually; no external ITA API integration exists.
**Files to touch:**
- `app/annual_reports/services/query_service.py` — add stub `submit_to_ita(report_id)` that posts to ITA API when configured
**Acceptance criteria:** When `ITA_API_URL` env var is set, submission POST hits the external API and stores the returned reference; when unset, falls back to manual reference input.

---

## [P3] 9.3 — טבלת השוואה רב-שנתית (Multi-Year Comparison Table)
**Status:** MISSING
**Gap:** No endpoint returns side-by-side metrics (income, expenses, profit, tax, effective rate) across multiple tax years for a client.
**Files to touch:**
- `app/annual_reports/api/annual_report_create_read.py` — add `GET /annual-reports/clients/{client_id}/multi-year-summary`
- `app/annual_reports/services/query_service.py` — add `get_multi_year_summary(client_id, years)` aggregating per-year financials
- `app/annual_reports/schemas/annual_report_detail.py` — add `MultiYearSummaryResponse` schema
**Acceptance criteria:** Endpoint accepts `?years=3` and returns array of `{tax_year, income, expenses, profit, tax_after_credits, effective_rate}`.

---

## [P3] 9.2 — שינוי YoY (Year-over-Year Change)
**Status:** MISSING
**Gap:** No endpoint or field calculates percentage change between consecutive tax years for any financial metric.
**Files to touch:**
- `app/annual_reports/services/query_service.py` — compute YoY delta within `get_multi_year_summary()` (depends on 9.3)
- `app/annual_reports/schemas/annual_report_detail.py` — add `yoy_change_pct` to each year row
**Acceptance criteria:** Multi-year summary response includes `yoy_change_pct` for income, profit, and tax fields.

---

## [P3] 9.4 — מעקב שיעור מס אפקטיבי (Effective Rate Trend)
**Status:** PARTIAL
**Gap:** `effective_rate` exists per report but no aggregated trend/history endpoint exists across years for a client.
**Files to touch:**
- `app/annual_reports/services/query_service.py` — add `get_effective_rate_history(client_id)` (can be part of multi-year summary)
**Acceptance criteria:** Endpoint or multi-year summary returns `effective_rate` per year enabling trend visualisation.

---

## [P3] 10.1 — ייצוא PDF (PDF Export for Annual Reports)
**Status:** PARTIAL
**Gap:** PDF export exists only for the aging report; annual report and advance payment PDF exports are absent.
**Files to touch:**
- `app/annual_reports/api/annual_report_financials.py` — add `GET /annual-reports/{id}/export/pdf`
- `app/annual_reports/services/financial_service.py` — add `export_pdf(report_id)` generating report summary PDF
**Acceptance criteria:** `GET /annual-reports/{id}/export/pdf` returns a PDF with client info, income/expense breakdown, tax calculation, and submission status.

---

## [P3] 10.2 — ייצוא Excel (Excel Export for Annual Reports)
**Status:** PARTIAL
**Gap:** Excel export exists for aging report and client list but not for annual reports or advance payments.
**Files to touch:**
- `app/annual_reports/api/annual_report_financials.py` — add `GET /annual-reports/{id}/export/excel`
- `app/annual_reports/services/financial_service.py` — add `export_excel(report_id)`
**Acceptance criteria:** `GET /annual-reports/{id}/export/excel` returns `.xlsx` with financial detail rows.

---

## [P3] 10.5 — הורדת אישור הגשה (Submission Certificate Download)
**Status:** PARTIAL
**Gap:** `ita_reference` is stored but there is no endpoint to download or generate a submission confirmation certificate.
**Files to touch:**
- `app/annual_reports/api/annual_report_create_read.py` — add `GET /annual-reports/{id}/submission-certificate`
- `app/annual_reports/services/query_service.py` — generate PDF certificate with reference number, client, year, submission date
**Acceptance criteria:** Endpoint returns a PDF certificate when report status is SUBMITTED or later.

---

## [P3] 10.6 — ייצוא השוואה (Multi-Year Comparison Export)
**Status:** MISSING
**Gap:** No multi-year comparison endpoint exists (see 9.3), so no export is possible.
**Files to touch:**
- `app/annual_reports/api/annual_report_create_read.py` — add export variant of multi-year summary (depends on 9.3)
**Acceptance criteria:** `GET /annual-reports/clients/{client_id}/multi-year-summary/export` returns Excel with YoY comparison.

---

## [P4] 10.4 — הגשה לרשות — אינטגרציה (ITA External API)
**Status:** PARTIAL
**Gap:** Submission saves `ita_reference` manually; no real external ITA API call is made.
**Files to touch:**
- `app/annual_reports/services/query_service.py` — see 1.9
**Acceptance criteria:** (Same as 1.9 — tracked there.)

---

## [P3] 4.6 — אחוז רווח גולמי (Gross Profit Margin %)
**Status:** MISSING
**Gap:** `gross_margin_pct` is not computed or returned; no service calculates `gross_profit / total_income × 100`.
**Files to touch:**
- `app/annual_reports/services/financial_service.py` — compute `gross_margin_pct` where `total_income > 0`
- `app/annual_reports/schemas/annual_report_financials.py` — add `gross_margin_pct: Optional[float]`
**Acceptance criteria:** Tax calculation or detail response includes `gross_margin_pct` when income is non-zero.

---

## [P3] 4.8 — גרף השוואה רב-שנתי (Multi-Year Income/Expense Chart)
**Status:** MISSING
**Gap:** No endpoint returns income/expenses/profit/tax across multiple years for chart rendering.
**Files to touch:**
- `app/annual_reports/api/annual_report_create_read.py` — add multi-year summary endpoint (see 9.3)
**Acceptance criteria:** (Resolved by implementing 9.3.)

---

## [P3] 5.6 — הזדמנויות חיסכון (Savings Opportunities Engine)
**Status:** MISSING
**Gap:** No service analyzes the client's tax situation and suggests optimization actions (pension top-up, training fund, etc.).
**Files to touch:**
- `app/annual_reports/services/financial_service.py` — add `get_savings_opportunities(report_id)` returning ranked list of suggestions
- `app/annual_reports/api/annual_report_financials.py` — add `GET /annual-reports/{id}/savings-opportunities`
- `app/annual_reports/schemas/annual_report_financials.py` — add `SavingsOpportunity` schema
**Acceptance criteria:** Endpoint returns up to 5 actionable recommendations with estimated tax saving per action.

---

## [P3] 5.7 — השלמת פנסיה (Pension Top-Up Calculation)
**Status:** MISSING
**Gap:** No calculation determines the optimal additional pension contribution to maximize tax deduction within statutory limits.
**Files to touch:**
- `app/annual_reports/services/financial_service.py` — add `calculate_pension_topup(report_id)` as part of savings opportunities (5.6)
**Acceptance criteria:** Savings opportunities response includes a pension top-up item with `suggested_additional_contribution` and `estimated_tax_saving`.

---

## [P3] 5.8 — קרן השתלמות (Training Fund Optimization)
**Status:** MISSING
**Gap:** No calculation for training fund (קרן השתלמות) contribution ceiling or tax benefit exists.
**Files to touch:**
- `app/annual_reports/services/financial_service.py` — add training fund optimization logic within savings opportunities (5.6)
**Acceptance criteria:** Savings opportunities response includes training fund item when client has not maximized the statutory ceiling.
