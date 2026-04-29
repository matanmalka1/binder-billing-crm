from __future__ import annotations

from .types import DeadlineOverride

# ── דחיות וחריגים רשמיים ─────────────────────────────────────────────────────
# כל override כאן מייצג פרסום רשמי שמשנה מועד בסיסי.
# base_* בלוח הקבוע = המועד החוקי הרגיל.
# override_date = המועד האפקטיבי לאחר הפרסום.
#
# מבנה period: "YYYY-MM" לתקופות תקופתיות, "YYYY" לדוחות שנתיים.
# column: שם עמודת הלוח שמושפעת.

DEADLINE_OVERRIDES_2026: tuple[DeadlineOverride, ...] = (
    # פברואר 2026 — דחייה חריגה רשמית
    DeadlineOverride(
        period="2026-02",
        column="effective_vat_periodic_and_income_tax_advances",
        original_date="2026-03-16",
        override_date="2026-03-26",
        reason_he="דחייה חריגה שפורסמה על ידי רשות המסים עבור תקופת ינואר-פברואר 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-02",
        column="effective_income_tax_withholding",
        original_date="2026-03-16",
        override_date="2026-03-26",
        reason_he="דחייה חריגה — ניכוי במקור פברואר 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-02",
        column="effective_vat_detailed_pcn874",
        original_date="2026-03-23",
        override_date="2026-03-26",
        reason_he="דחייה חריגה — PCN874 פברואר 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    # מרץ 2026 — דחייה עקב פסח
    DeadlineOverride(
        period="2026-03",
        column="effective_vat_periodic_and_income_tax_advances",
        original_date="2026-04-15",
        override_date="2026-04-27",
        reason_he="דחייה עקב חג הפסח — תקופת מרץ 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-03",
        column="effective_income_tax_withholding",
        original_date="2026-04-15",
        override_date="2026-04-27",
        reason_he="דחייה עקב פסח — ניכוי במקור מרץ 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-03",
        column="effective_vat_detailed_pcn874",
        original_date="2026-04-23",
        override_date="2026-04-27",
        reason_he="דחייה עקב פסח — PCN874 מרץ 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    # אוגוסט 2026 — דחייה עקב ראש השנה/יום כיפור
    DeadlineOverride(
        period="2026-08",
        column="effective_vat_periodic_and_income_tax_advances",
        original_date="2026-09-15",
        override_date="2026-09-24",
        reason_he="דחייה עקב חגי תשרי (ראש השנה/יום כיפור) — תקופת אוגוסט 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-08",
        column="effective_income_tax_withholding",
        original_date="2026-09-15",
        override_date="2026-09-24",
        reason_he="דחייה עקב חגי תשרי — ניכוי במקור אוגוסט 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    # ספטמבר 2026 — דחייה עקב סוכות
    DeadlineOverride(
        period="2026-09",
        column="effective_vat_periodic_and_income_tax_advances",
        original_date="2026-10-15",
        override_date="2026-10-19",
        reason_he="דחייה עקב חגי תשרי (סוכות) — תקופת ספטמבר 2026.",
        source_id="tax_authority_2026_calendar",
    ),
    DeadlineOverride(
        period="2026-09",
        column="effective_income_tax_withholding",
        original_date="2026-10-15",
        override_date="2026-10-19",
        reason_he="דחייה עקב סוכות — ניכוי במקור ספטמבר 2026.",
        source_id="tax_authority_2026_calendar",
    ),
)

# דחיות בדוחות שנתיים — שנת מס 2025 (מוגש ב-2026)
ANNUAL_OVERRIDES_TAX_YEAR_2025: tuple[DeadlineOverride, ...] = (
    DeadlineOverride(
        period="2025",
        column="individual_1301_due_date",
        original_date="2026-05-31",
        override_date="2026-06-30",
        reason_he="דחייה חריגה לשנת מס 2025 — יחידים חייבים בדוח מקוון.",
        source_id="tax_authority_2025_annual_extension",
    ),
    DeadlineOverride(
        period="2025",
        column="company_1214_due_date",
        original_date="2026-07-31",
        override_date="2026-07-30",
        reason_he="דחייה חריגה לשנת מס 2025 — חברות.",
        source_id="tax_authority_2025_annual_extension",
    ),
    DeadlineOverride(
        period="2025",
        column="small_business_due_date",
        original_date="2026-04-30",
        override_date="2026-05-31",
        reason_he="אורכה לעסק זעיר לשנת מס 2025.",
        source_id="tax_authority_small_business_2025_extension",
    ),
)

# lookup: period + column -> override_date
def get_override(
    period: str,
    column: str,
    overrides: tuple[DeadlineOverride, ...] = DEADLINE_OVERRIDES_2026,
) -> str | None:
    for o in overrides:
        if o.period == period and o.column == column:
            return o.override_date
    return None
