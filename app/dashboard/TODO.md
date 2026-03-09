## [P2] 9.1 — לוח KPI — 5 כרטיסים (Dashboard KPI Cards)
**Status:** PARTIAL
**Gap:** Dashboard overview returns `binders_in_office` and `attention_items` counts, but tax KPIs (`gross_income`, `net_profit`, `total_deductions` aggregated across clients) are absent.
**Files to touch:**
- `app/dashboard/services/dashboard_service.py` — add `get_tax_kpis(year)` aggregating `gross_income`, `net_profit`, `total_tax_collected`, `avg_effective_rate` across all clients for a given tax year
- `app/dashboard/api/dashboard.py` — add `GET /dashboard/tax-kpis?year=` endpoint
- `app/dashboard/schemas/dashboard.py` — add `TaxKPIResponse` schema
**Acceptance criteria:** `GET /dashboard/tax-kpis?year=2024` returns `{gross_income_total, net_profit_total, total_tax_collected, avg_effective_rate, client_count}` for all clients with a report in that year.

---

## [P3] 9.5 — מעקב שולי רווח (Gross Profit Margin Tracking)
**Status:** MISSING
**Gap:** `gross_profit_margin` % is not computed in any dashboard or report service.
**Files to touch:**
- `app/dashboard/services/dashboard_service.py` — include `avg_gross_margin_pct` in `get_tax_kpis()` (depends on 9.1)
**Acceptance criteria:** Tax KPI response includes `avg_gross_margin_pct` across all active clients for the year.

---

## [P3] 9.6 — שיעור גביית מקדמות — Dashboard (Collection Rate on Dashboard)
**Status:** MISSING
**Gap:** Advance payment `collection_rate` is not surfaced on the dashboard.
**Files to touch:**
- `app/dashboard/services/dashboard_service.py` — add advance payment collection rate to dashboard KPIs by querying advance payments aggregate
**Acceptance criteria:** Dashboard KPI response includes `advance_collection_rate_pct` for the current year.

---

## [P3] 9.7 — אגרגציה חבות כוללת (Total Liability Aggregation)
**Status:** PARTIAL
**Gap:** Income tax + advances are in the tax engine, but national insurance and VAT liabilities are not included in any aggregate total-liability figure across the dashboard.
**Files to touch:**
- `app/dashboard/services/dashboard_service.py` — fetch NI totals (once 2.7 is implemented) and VAT balance per client, sum into `total_liability_estimate`
**Acceptance criteria:** Dashboard or per-report response exposes a `total_liability` that sums income tax + NI + VAT − advances paid.
