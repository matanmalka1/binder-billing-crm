from __future__ import annotations

from .types import VatDeductionRule

# ── חוקי ניכוי תשומות מע"מ — ישראל ──────────────────────────────────────────
# מקור: חוק מס ערך מוסף, סעיפים 38–41.
# rate: 0.0 = ללא ניכוי, 0.6667 = 2/3, 0.25 = 1/4, 1.0 = ניכוי מלא.
#
# אזהרה: שיעור רכב (2/3 מול 1/4) תלוי בסוג הרכב ושימושו.
# אין לקודד אוטומציה שמניחה 2/3 לכל רכב ללא בדיקת סיווג.

VAT_DEDUCTION_RULES: tuple[VatDeductionRule, ...] = (
    # ── ניכוי מלא — 100% ─────────────────────────────────────────────────────
    VatDeductionRule(
        category="inventory",
        rate=1.0,
        label_he="קניית סחורה / מלאי",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="office",
        rate=1.0,
        label_he="משרד",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="professional_services",
        rate=1.0,
        label_he="שירותים מקצועיים",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="equipment",
        rate=1.0,
        label_he="ציוד",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="rent",
        rate=1.0,
        label_he="שכירות",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="marketing",
        rate=1.0,
        label_he="שיווק",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="maintenance",
        rate=1.0,
        label_he="תחזוקה",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="utilities",
        rate=1.0,
        label_he="חשמל ומים",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="postage_and_shipping",
        rate=1.0,
        label_he="משלוחים ודואר",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="bank_fees",
        rate=1.0,
        label_he="עמלות בנק",
        source_ids=("tax_authority_vat_law_38_41",),
    ),

    # ── ניכוי חלקי 2/3 — הוצאות מעורבות ─────────────────────────────────────
    VatDeductionRule(
        category="travel",
        rate=0.6667,
        label_he="נסיעות",
        condition_he="הוצאה מעורבת — 2/3 ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="fuel",
        rate=0.6667,
        label_he="דלק",
        condition_he="הוצאה מעורבת — 2/3 ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="communication",
        rate=0.6667,
        label_he="תקשורת",
        condition_he="הוצאה מעורבת — 2/3 ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="tolls_and_parking",
        rate=0.6667,
        label_he="חניה וכבישי אגרה",
        condition_he="הוצאה מעורבת — 2/3 ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="mixed_expense",
        rate=0.6667,
        label_he="הוצאה מעורבת",
        condition_he="ברירת מחדל שמרנית להוצאה מעורבת שלא סווגה.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),

    # ── רכב — שיעור תלוי סוג ─────────────────────────────────────────────────
    # רכב פרטי (לפי תקנות): 2/3 ניכוי.
    # רכב מסחרי (משא, אמבולנס, וכו'): ניכוי מלא — מחוץ לטבלה זו.
    # ליסינג: אותו שיעור כמו הרכב עצמו.
    VatDeductionRule(
        category="vehicle",
        rate=0.6667,
        label_he="רכב פרטי",
        condition_he=(
            "רכב פרטי — 2/3 ניכוי. "
            "רכב מסחרי/מיוחד עשוי להיות זכאי לניכוי מלא — יש לסווג בנפרד."
        ),
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="vehicle_maintenance",
        rate=0.6667,
        label_he="תחזוקת רכב פרטי",
        condition_he="2/3 ניכוי — כרכב עצמו.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="vehicle_leasing",
        rate=0.6667,
        label_he="ליסינג רכב פרטי",
        condition_he="2/3 ניכוי — כרכב עצמו.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),

    # ── ללא ניכוי — 0% ───────────────────────────────────────────────────────
    VatDeductionRule(
        category="salary",
        rate=0.0,
        label_he="שכר עבודה",
        condition_he="שכר אינו תשומת מע״מ — ללא ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="entertainment",
        rate=0.0,
        label_he="אירוח וכיבוד",
        condition_he="אסור לניכוי לפי סעיף 41 לחוק מע״מ.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="gifts",
        rate=0.0,
        label_he="מתנות",
        condition_he="אסור לניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="vehicle_insurance",
        rate=0.0,
        label_he="ביטוח רכב",
        condition_he="ביטוח — אין מע״מ, ללא ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="insurance",
        rate=0.0,
        label_he="ביטוח כללי",
        condition_he="ביטוח — אין מע״מ, ללא ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
    VatDeductionRule(
        category="municipal_tax",
        rate=0.0,
        label_he="ארנונה",
        condition_he="ארנונה — אין מע״מ, ללא ניכוי.",
        source_ids=("tax_authority_vat_law_38_41",),
    ),
)

# lookup מהיר לפי קטגוריה
VAT_DEDUCTION_RATE_BY_CATEGORY: dict[str, float] = {
    r.category: r.rate for r in VAT_DEDUCTION_RULES
}
