from __future__ import annotations

from ..types import CreditPointConfig, FinancialConstant, IncomeTaxBracket, RateBracket

# ── קבועים כספיים — שנת מס 2024 ──────────────────────────────────────────────
# מקורות: כל זכות נתוני עבר, חוברת ניכויים רשות המסים 2024

CONSTANTS_2024: dict[str, FinancialConstant] = {
    "vat_rate_percent": FinancialConstant(
        id="vat_rate_percent",
        year=2024,
        value=17.0,
        unit="percent",
        effective_from="2024-01-01",
        effective_to="2024-12-31",
        source_ids=("tax_authority_vat_amounts_2026",),
        note_he="שיעור מע״מ לשנת 2024 — 17%. עלה ל-18% ב-2025.",
    ),
    "credit_point_value_ils": FinancialConstant(
        id="credit_point_value_ils",
        year=2024,
        value=2_904,
        unit="ILS/year",
        effective_from="2024-01-01",
        effective_to="2024-12-31",
        source_ids=("tax_authority_credit_points_2024",),
        note_he="שווי נקודת זיכוי אחת לשנת 2024 — 242₪/חודש.",
    ),
    "vat_statutory_deadline_day": FinancialConstant(
        id="vat_statutory_deadline_day",
        year=2024,
        value=15,
        unit="day_of_month",
        effective_from="2024-01-01",
        effective_to="2024-12-31",
        source_ids=("tax_authority_vat_amounts_2024",),
        note_he="המועד החוקי הבסיסי להגשת דוח מע״מ — ה-15 בחודש.",
    ),
    "vat_online_extended_deadline_day": FinancialConstant(
        id="vat_online_extended_deadline_day",
        year=2024,
        value=19,
        unit="day_of_month",
        effective_from="2024-01-01",
        effective_to="2024-12-31",
        source_ids=("tax_authority_vat_amounts_2024",),
        note_he="הארכה לדיווח דיגיטלי בלבד — ה-19 בחודש.",
    ),
    "advance_payment_due_day": FinancialConstant(
        id="advance_payment_due_day",
        year=2024,
        value=15,
        unit="day_of_month",
        effective_from="2024-01-01",
        effective_to="2024-12-31",
        source_ids=("tax_authority_vat_amounts_2024",),
        note_he="מועד תשלום מקדמות מס הכנסה — ה-15 בחודש.",
    ),
}

# ── מדרגות מס הכנסה ליחיד — 2024 ─────────────────────────────────────────────
# מקור: כל זכות נתוני עבר
# אימות: 84,120 / 120,720 / 193,800 / 269,280 / 560,280 / 721,560
# שים לב: הקוד הישן ב-tax_engine.py הציג 81,480 תחת 2024 — שגוי, אלו מדרגות 2023.

INCOME_TAX_BRACKETS_2024: tuple[IncomeTaxBracket, ...] = (
    IncomeTaxBracket(from_ils=0,       up_to_ils=84_120,  rate=0.10, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=84_121,  up_to_ils=120_720, rate=0.14, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=120_721, up_to_ils=193_800, rate=0.20, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=193_801, up_to_ils=269_280, rate=0.31, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=269_281, up_to_ils=560_280, rate=0.35, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=560_281, up_to_ils=721_560, rate=0.47, source_ids=("tax_authority_income_tax_brackets_2024",)),
    IncomeTaxBracket(from_ils=721_561, up_to_ils=None,    rate=0.50, source_ids=("tax_authority_income_tax_brackets_2024",)),
)

# ── נקודת זיכוי — 2024 ───────────────────────────────────────────────────────
CREDIT_POINT_2024 = CreditPointConfig(
    year=2024,
    monthly_value_ils=242,
    annual_value_ils=2_904,
    default_resident_points=2.25,
    default_female_resident_points=2.75,
    source_ids=("tax_authority_credit_points_2024",),
)

# ── ביטוח לאומי עצמאי — 2024 ─────────────────────────────────────────────────
NI_BRACKETS_2024: tuple[RateBracket, ...] = (
    RateBracket(
        up_to_ils=6_331,
        rate_percent=6.72,
        label_he="שיעור מופחת לעצמאי — 2024",
    ),
    RateBracket(
        up_to_ils=49_030,
        rate_percent=15.46,
        label_he="שיעור רגיל לעצמאי — 2024",
    ),
)
