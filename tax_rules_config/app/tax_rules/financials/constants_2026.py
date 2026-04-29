from __future__ import annotations

from ..types import FinancialConstant, RateBracket

# ── קבועים כספיים — שנת מס 2026 ──────────────────────────────────────────────
# מקורות: רשות המסים, ביטוח לאומי, חוזרים שנתיים

CONSTANTS_2026: dict[str, FinancialConstant] = {
    # מע"מ
    "vat_rate_percent": FinancialConstant(
        id="vat_rate_percent",
        year=2026,
        value=18.0,
        unit="percent",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="שיעור מע״מ כללי לשנת 2026. לא לקודד בלוגיקה עסקית — תמיד לקרוא מהקונפיג.",
    ),
    "osek_patur_ceiling_ils": FinancialConstant(
        id="osek_patur_ceiling_ils",
        year=2026,
        value=122_833,
        unit="ILS/year",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="תקרת מחזור שנתית לעוסק פטור 2026. חובה לעדכן בכל שנת מס.",
    ),
    "exceptional_invoice_threshold_ils": FinancialConstant(
        id="exceptional_invoice_threshold_ils",
        year=2026,
        value=25_000,
        unit="ILS",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="חשבונית מעל סכום זה דורשת דיווח מיוחד (חשבונית ישראל).",
    ),
    "israel_invoice_mandatory_threshold_ils": FinancialConstant(
        id="israel_invoice_mandatory_threshold_ils",
        year=2026,
        value=5_000,
        unit="ILS",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="חשבונית ישראל חובה מעל סכום זה (שלב יישום 2026).",
    ),

    # נקודת זיכוי מס הכנסה
    "credit_point_value_ils": FinancialConstant(
        id="credit_point_value_ils",
        year=2026,
        value=2_904,
        unit="ILS/year",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_credit_points_2026",),
        note_he="שווי נקודת זיכוי שנתית לשנת 2026.",
    ),

    # ביטוח לאומי — עצמאי
    "btl_average_wage_ils_monthly": FinancialConstant(
        id="btl_average_wage_ils_monthly",
        year=2026,
        value=13_769,
        unit="ILS/month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("btl_2026_constants_circular",),
        note_he="שכר ממוצע במשק לצורך חישוב דמי ביטוח לאומי 2026.",
    ),
    "btl_reduced_rate_ceiling_ils_monthly": FinancialConstant(
        id="btl_reduced_rate_ceiling_ils_monthly",
        year=2026,
        value=7_703,
        unit="ILS/month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("btl_self_employed_rates_2026", "btl_2026_constants_circular"),
        note_he="60% מהשכר הממוצע — תקרת מדרגה מופחתת לעצמאי.",
    ),
    "btl_maximum_income_ils_monthly": FinancialConstant(
        id="btl_maximum_income_ils_monthly",
        year=2026,
        value=51_910,
        unit="ILS/month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("btl_self_employed_rates_2026", "btl_2026_constants_circular"),
        note_he="הכנסה מרבית לתשלום דמי ביטוח לאומי עצמאי 2026.",
    ),
    "btl_minimum_income_ils_monthly": FinancialConstant(
        id="btl_minimum_income_ils_monthly",
        year=2026,
        value=3_442,
        unit="ILS/month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("btl_self_employed_rates_2026",),
        note_he="הכנסה מזערית לתשלום דמי ביטוח לאומי עצמאי 2026.",
    ),
}

# מדרגות ביטוח לאומי עצמאי — 2026
NI_BRACKETS_2026: tuple[RateBracket, ...] = (
    RateBracket(
        up_to_ils=7_703,
        rate_percent=6.92,
        label_he="שיעור מופחת לעצמאי עד 60% מהשכר הממוצע — 2026",
    ),
    RateBracket(
        up_to_ils=51_910,
        rate_percent=15.79,
        label_he="שיעור רגיל לעצמאי מעל המדרגה המופחתת — 2026",
    ),
)
