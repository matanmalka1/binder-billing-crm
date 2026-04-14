"""
Constants for the tax_deadline domain.

Israeli fiscal due dates:
- VAT (מע"מ): filed on the 19th of the month following the reporting period.
- Advance payments (מקדמות מס הכנסה): due on the 15th of each month.
- Annual report (דוח שנתי): varies by filing profile and channel.
"""

from datetime import date

# ── Israeli fiscal due-day constants ─────────────────────────────────────────
VAT_FILING_DUE_DAY = 19        # 19th of following month — applies to both MONTHLY and BIMONTHLY VAT
ADVANCE_PAYMENT_DUE_DAY = 15   # 15th of each month (מקדמות)
# ── Urgency thresholds ────────────────────────────────────────────────────────
# MUST MATCH frontend src/features/taxDeadlines/utils.ts urgency thresholds
URGENCY_RED_DAYS = 2           # ≤ 2 days remaining → RED
URGENCY_YELLOW_DAYS = 7        # ≤ 7 days remaining → YELLOW

# ── Safety ceiling for global (non-client-scoped) deadline list ───────────────
# Architectural debt — proper fix is DB-level pagination (see CLAUDE.md).
GLOBAL_DEADLINE_FETCH_LIMIT = 500

# ── Sentinel upper bound for "all pending" query ──────────────────────────────
FAR_FUTURE_DATE = date(2099, 12, 31)
