"""
Constants for the tax_deadline domain.

Israeli fiscal due dates:
- VAT (מע"מ): statutory deadline is the 15th; extended digital deadline is the 19th (VAT_ONLINE_EXTENDED_DEADLINE_DAY from vat_reports).
- Advance payments (מקדמות מס הכנסה): due on the 15th of each month.
- Annual report (דוח שנתי): varies by filing profile and channel.
"""

from datetime import date

# ── Israeli fiscal due-day constants ─────────────────────────────────────────
ADVANCE_PAYMENT_DUE_DAY = 15   # 15th of each month (מקדמות)
# ── Urgency thresholds ────────────────────────────────────────────────────────
URGENCY_CRITICAL_DAYS = 2      # ≤ 2 days remaining → critical
URGENCY_WARNING_DAYS = 7       # ≤ 7 days remaining → warning

# ── Safety ceiling for global (non-client-scoped) deadline list ───────────────
# Architectural debt — proper fix is DB-level pagination (see CLAUDE.md).
GLOBAL_DEADLINE_FETCH_LIMIT = 500

# ── Sentinel upper bound for "all pending" query ──────────────────────────────
FAR_FUTURE_DATE = date(2099, 12, 31)
