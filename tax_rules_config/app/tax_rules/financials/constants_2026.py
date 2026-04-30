from __future__ import annotations

from ..types import CreditPointConfig, FinancialConstant, IncomeTaxBracket, RateBracket

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
    # מועדי הגשה חוקיים
    "vat_statutory_deadline_day": FinancialConstant(
        id="vat_statutory_deadline_day",
        year=2026,
        value=15,
        unit="day_of_month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="המועד החוקי הבסיסי להגשת דוח מע״מ — ה-15 בחודש. לא להחליף עם המועד המורחב (19).",
    ),
    "vat_online_extended_deadline_day": FinancialConstant(
        id="vat_online_extended_deadline_day",
        year=2026,
        value=19,
        unit="day_of_month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="הארכה לדיווח דיגיטלי בלבד — ה-19 בחודש. זכות, לא בסיס חוקי.",
    ),
    "advance_payment_due_day": FinancialConstant(
        id="advance_payment_due_day",
        year=2026,
        value=15,
        unit="day_of_month",
        effective_from="2026-01-01",
        effective_to=None,
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="מועד תשלום מקדמות מס הכנסה — ה-15 בחודש.",
    ),
}

# ── מדרגות מס הכנסה ליחיד — 2026 ─────────────────────────────────────────────
# מקור: כל זכות + חוברת ניכויים רשות המסים אפריל 2026
# שינוי מ-2025: מדרגת 20% הורחבה מ-193,800 ל-228,000; מדרגת 31% מ-269,280 ל-301,200
# אימות: gov.il/BlobFolder/...monthly-deductions-booklet-2026.pdf

INCOME_TAX_BRACKETS_2026: tuple[IncomeTaxBracket, ...] = (
    IncomeTaxBracket(from_ils=0,       up_to_ils=84_120,  rate=0.10, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=84_121,  up_to_ils=120_720, rate=0.14, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=120_721, up_to_ils=228_000, rate=0.20, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=228_001, up_to_ils=301_200, rate=0.31, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=301_201, up_to_ils=560_280, rate=0.35, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=560_281, up_to_ils=721_560, rate=0.47, source_ids=("tax_authority_income_tax_brackets_2026",)),
    IncomeTaxBracket(from_ils=721_561, up_to_ils=None,    rate=0.50, source_ids=("tax_authority_income_tax_brackets_2026",)),
)

# ── נקודת זיכוי — 2026 ───────────────────────────────────────────────────────
# 2,904₪/שנה = שווי נקודה אחת. תושב ישראל מקבל 2.25 נקודות (6,534₪); אישה 2.75 (7,986₪).
CREDIT_POINT_2026 = CreditPointConfig(
    year=2026,
    monthly_value_ils=242,
    annual_value_ils=2_904,
    default_resident_points=2.25,
    default_female_resident_points=2.75,
    source_ids=("tax_authority_credit_points_2026",),
)

# ── ביטוח לאומי עצמאי — 2026
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
