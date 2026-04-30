from __future__ import annotations

from ..types import CreditPointConfig, FinancialConstant, IncomeTaxBracket, RateBracket

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
    "vat_statutory_deadline_day": FinancialConstant(
        id="vat_statutory_deadline_day",
        year=2025,
        value=15,
        unit="day_of_month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2025",),
        note_he="המועד החוקי הבסיסי להגשת דוח מע״מ — ה-15 בחודש.",
    ),
    "vat_online_extended_deadline_day": FinancialConstant(
        id="vat_online_extended_deadline_day",
        year=2025,
        value=19,
        unit="day_of_month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2025",),
        note_he="הארכה לדיווח דיגיטלי בלבד — ה-19 בחודש.",
    ),
    "advance_payment_due_day": FinancialConstant(
        id="advance_payment_due_day",
        year=2025,
        value=15,
        unit="day_of_month",
        effective_from="2025-01-01",
        effective_to="2025-12-31",
        source_ids=("tax_authority_vat_amounts_2025",),
        note_he="מועד תשלום מקדמות מס הכנסה — ה-15 בחודש.",
    ),
}

# ── מדרגות מס הכנסה ליחיד — 2025 ─────────────────────────────────────────────
# מקור: כל זכות נתוני עבר — זהות ל-2024
# אימות: 84,120 / 120,720 / 193,800 / 269,280 / 560,280 / 721,560

INCOME_TAX_BRACKETS_2025: tuple[IncomeTaxBracket, ...] = (
    IncomeTaxBracket(from_ils=0,       up_to_ils=84_120,  rate=0.10, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=84_121,  up_to_ils=120_720, rate=0.14, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=120_721, up_to_ils=193_800, rate=0.20, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=193_801, up_to_ils=269_280, rate=0.31, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=269_281, up_to_ils=560_280, rate=0.35, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=560_281, up_to_ils=721_560, rate=0.47, source_ids=("tax_authority_income_tax_brackets_2025",)),
    IncomeTaxBracket(from_ils=721_561, up_to_ils=None,    rate=0.50, source_ids=("tax_authority_income_tax_brackets_2025",)),
)

# ── נקודת זיכוי — 2025 ───────────────────────────────────────────────────────
CREDIT_POINT_2025 = CreditPointConfig(
    year=2025,
    monthly_value_ils=235,
    annual_value_ils=2_820,
    default_resident_points=2.25,
    default_female_resident_points=2.75,
    source_ids=("tax_authority_credit_points_2025",),
)

# ── ביטוח לאומי עצמאי — 2025
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
