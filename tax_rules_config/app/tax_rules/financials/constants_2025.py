from __future__ import annotations

from ..types import FinancialConstant, RateBracket

# ── קבועים כספיים — שנת מס 2025 ──────────────────────────────────────────────
# מקורות: רשות המסים, ביטוח לאומי, חוזרים שנתיים

CONSTANTS_2025: dict[str, FinancialConstant] = {
    # מע"מ
    "vat_rate_percent": FinancialConstant(
        id="vat_rate_percent",
        year=2025,
        value=18.0,
        unit="percent",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="שיעור מע״מ כללי לשנת 2025.",
    ),
    "osek_patur_ceiling_ils": FinancialConstant(
        id="osek_patur_ceiling_ils",
        year=2025,
        value=120_000,
        unit="ILS/year",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="תקרת מחזור שנתית לעוסק פטור 2025.",
    ),
    "exceptional_invoice_threshold_ils": FinancialConstant(
        id="exceptional_invoice_threshold_ils",
        year=2025,
        value=25_000,
        unit="ILS",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="חשבונית מעל סכום זה דורשת דיווח מיוחד (חשבונית ישראל).",
    ),

    # נקודת זיכוי מס הכנסה
    "credit_point_value_ils": FinancialConstant(
        id="credit_point_value_ils",
        year=2025,
        value=2_820,
        unit="ILS/year",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_credit_points_2025",),
        note_he="שווי נקודת זיכוי שנתית לשנת 2025.",
    ),

    # ביטוח לאומי — עצמאי
    "btl_average_wage_ils_monthly": FinancialConstant(
        id="btl_average_wage_ils_monthly",
        year=2025,
        value=13_137,
        unit="ILS/month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("btl_2025_constants_circular",),
        note_he="שכר ממוצע במשק לצורך חישוב דמי ביטוח לאומי 2025.",
    ),
    "btl_reduced_rate_ceiling_ils_monthly": FinancialConstant(
        id="btl_reduced_rate_ceiling_ils_monthly",
        year=2025,
        value=6_331,
        unit="ILS/month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("btl_2025_constants_circular",),
        note_he="60% מהשכר הממוצע — תקרת מדרגה מופחתת לעצמאי.",
    ),
    "btl_maximum_income_ils_monthly": FinancialConstant(
        id="btl_maximum_income_ils_monthly",
        year=2025,
        value=49_030,
        unit="ILS/month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("btl_2025_constants_circular",),
        note_he="הכנסה מרבית לתשלום דמי ביטוח לאומי עצמאי 2025.",
    ),
    "btl_minimum_income_ils_monthly": FinancialConstant(
        id="btl_minimum_income_ils_monthly",
        year=2025,
        value=3_285,
        unit="ILS/month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("btl_2025_constants_circular",),
        note_he="הכנסה מזערית לתשלום דמי ביטוח לאומי עצמאי 2025.",
    ),
}

# מדרגות ביטוח לאומי עצמאי — 2025
NI_BRACKETS_2025: tuple[RateBracket, ...] = (
    RateBracket(
        up_to_ils=6_331,
        rate_percent=6.72,
        label_he="שיעור מופחת לעצמאי עד 60% מהשכר הממוצע — 2025",
    ),
    RateBracket(
        up_to_ils=49_030,
        rate_percent=15.46,
        label_he="שיעור רגיל לעצמאי מעל המדרגה המופחתת — 2025",
    ),
)
