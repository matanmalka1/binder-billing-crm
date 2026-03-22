"""
Constants for the tax_deadline domain.

Israeli fiscal due dates:
- VAT (מע"מ): filed on the 19th of the month following the reporting period.
- Advance payments (מקדמות מס הכנסה): due on the 15th of each month.
- Annual report (דוח שנתי): April 30 of the year following the tax year.
"""

from datetime import date

# ── Israeli fiscal due-day constants ─────────────────────────────────────────
VAT_FILING_DUE_DAY = 19        # 19th of following month — applies to both MONTHLY and BIMONTHLY VAT
ADVANCE_PAYMENT_DUE_DAY = 15   # 15th of each month (מקדמות)
ANNUAL_REPORT_DUE_MONTH = 4    # April
ANNUAL_REPORT_DUE_DAY = 30     # April 30 of year+1

# ── Urgency thresholds ────────────────────────────────────────────────────────
URGENCY_RED_DAYS = 2           # ≤ 2 days remaining → RED
URGENCY_YELLOW_DAYS = 7        # ≤ 7 days remaining → YELLOW

# ── Safety ceiling for global (non-client-scoped) deadline list ───────────────
# Architectural debt — proper fix is DB-level pagination (see CLAUDE.md).
GLOBAL_DEADLINE_FETCH_LIMIT = 500

# ── Sentinel upper bound for "all pending" query ──────────────────────────────
FAR_FUTURE_DATE = date(2099, 12, 31)
