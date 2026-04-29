from __future__ import annotations

# לוח מועדים רשמי — שנת מס 2026
#
# מפתח: "YYYY-MM" = תקופת הדיווח.
# לדו-חודשי: המפתח הוא החודש השני של התקופה (ינואר-פברואר => "2026-02").
#
# עמודות:
#   base_*      = מועד חוקי/בסיסי לפי לוח רשות המסים השנתי.
#   effective_* = לאחר דחיות חריגות רשמיות (אם אין דחייה = זהה ל-base).
#
# מקורות:
#   - tax_authority_2026_calendar: לוח מועדי מע״מ, מקדמות, ניכויים — רשות המסים 2026
#   - btl_employer_102_due: מועדי ביטוח לאומי מעסיק — ב"ל
#
# אזהרה: דצמבר 2026 מוגש בינואר 2027 — מועדים נגזרים עד פרסום לוח 2027.

PERIODIC_TAX_AUTHORITY_DUE_DATES_2026: dict[str, dict[str, str]] = {
    "2026-01": {
        # VAT תקופתי + מקדמות מס הכנסה
        "base_vat_periodic_and_income_tax_advances":      "2026-02-16",
        "effective_vat_periodic_and_income_tax_advances": "2026-02-16",
        # ניכוי במקור (102 מ"ה)
        "base_income_tax_withholding":      "2026-02-16",
        "effective_income_tax_withholding": "2026-02-16",
        # PCN874
        "base_vat_detailed_pcn874":      "2026-02-23",
        "effective_vat_detailed_pcn874": "2026-02-23",
        # ביטוח לאומי מעסיק (102 ב"ל) — תמיד ה-15, אין לוח רשמי נפרד
        "btl_employer_102_due_day": "15",
    },
    "2026-02": {
        "base_vat_periodic_and_income_tax_advances":      "2026-03-16",
        "effective_vat_periodic_and_income_tax_advances": "2026-03-26",
        "base_income_tax_withholding":      "2026-03-16",
        "effective_income_tax_withholding": "2026-03-26",
        "base_vat_detailed_pcn874":      "2026-03-23",
        "effective_vat_detailed_pcn874": "2026-03-26",
        "btl_employer_102_due_day": "15",
        "override_note_he": "דחייה חריגה לפרסום רשות המסים — פברואר/ינואר-פברואר 2026.",
        "override_source_id": "tax_authority_2026_calendar",
    },
    "2026-03": {
        "base_vat_periodic_and_income_tax_advances":      "2026-04-27",
        "effective_vat_periodic_and_income_tax_advances": "2026-04-27",
        "base_income_tax_withholding":      "2026-04-27",
        "effective_income_tax_withholding": "2026-04-27",
        "base_vat_detailed_pcn874":      "2026-04-23",
        "effective_vat_detailed_pcn874": "2026-04-27",
        "btl_employer_102_due_day": "15",
        "override_note_he": "דחייה עקב פסח 2026.",
    },
    "2026-04": {
        "base_vat_periodic_and_income_tax_advances":      "2026-05-18",
        "effective_vat_periodic_and_income_tax_advances": "2026-05-18",
        "base_income_tax_withholding":      "2026-05-18",
        "effective_income_tax_withholding": "2026-05-18",
        "base_vat_detailed_pcn874":      "2026-05-23",
        "effective_vat_detailed_pcn874": "2026-05-26",
        "btl_employer_102_due_day": "15",
    },
    "2026-05": {
        "base_vat_periodic_and_income_tax_advances":      "2026-06-15",
        "effective_vat_periodic_and_income_tax_advances": "2026-06-15",
        "base_income_tax_withholding":      "2026-06-16",
        "effective_income_tax_withholding": "2026-06-16",
        "base_vat_detailed_pcn874":      "2026-06-23",
        "effective_vat_detailed_pcn874": "2026-06-23",
        "btl_employer_102_due_day": "15",
    },
    "2026-06": {
        "base_vat_periodic_and_income_tax_advances":      "2026-07-15",
        "effective_vat_periodic_and_income_tax_advances": "2026-07-15",
        "base_income_tax_withholding":      "2026-07-16",
        "effective_income_tax_withholding": "2026-07-16",
        "base_vat_detailed_pcn874":      "2026-07-23",
        "effective_vat_detailed_pcn874": "2026-07-27",
        "btl_employer_102_due_day": "15",
    },
    "2026-07": {
        "base_vat_periodic_and_income_tax_advances":      "2026-08-17",
        "effective_vat_periodic_and_income_tax_advances": "2026-08-17",
        "base_income_tax_withholding":      "2026-08-17",
        "effective_income_tax_withholding": "2026-08-17",
        "base_vat_detailed_pcn874":      "2026-08-23",
        "effective_vat_detailed_pcn874": "2026-08-24",
        "btl_employer_102_due_day": "15",
    },
    "2026-08": {
        "base_vat_periodic_and_income_tax_advances":      "2026-09-24",
        "effective_vat_periodic_and_income_tax_advances": "2026-09-24",
        "base_income_tax_withholding":      "2026-09-24",
        "effective_income_tax_withholding": "2026-09-24",
        "base_vat_detailed_pcn874":      "2026-09-23",
        "effective_vat_detailed_pcn874": "2026-09-24",
        "btl_employer_102_due_day": "15",
        "override_note_he": "דחייה עקב ראש השנה/יום כיפור 2026.",
    },
    "2026-09": {
        "base_vat_periodic_and_income_tax_advances":      "2026-10-19",
        "effective_vat_periodic_and_income_tax_advances": "2026-10-19",
        "base_income_tax_withholding":      "2026-10-19",
        "effective_income_tax_withholding": "2026-10-19",
        "base_vat_detailed_pcn874":      "2026-10-23",
        "effective_vat_detailed_pcn874": "2026-10-26",
        "btl_employer_102_due_day": "15",
        "override_note_he": "דחייה עקב חגי תשרי 2026.",
    },
    "2026-10": {
        "base_vat_periodic_and_income_tax_advances":      "2026-11-16",
        "effective_vat_periodic_and_income_tax_advances": "2026-11-16",
        "base_income_tax_withholding":      "2026-11-16",
        "effective_income_tax_withholding": "2026-11-16",
        "base_vat_detailed_pcn874":      "2026-11-23",
        "effective_vat_detailed_pcn874": "2026-11-23",
        "btl_employer_102_due_day": "15",
    },
    "2026-11": {
        "base_vat_periodic_and_income_tax_advances":      "2026-12-15",
        "effective_vat_periodic_and_income_tax_advances": "2026-12-15",
        "base_income_tax_withholding":      "2026-12-16",
        "effective_income_tax_withholding": "2026-12-16",
        "base_vat_detailed_pcn874":      "2026-12-23",
        "effective_vat_detailed_pcn874": "2026-12-23",
        "btl_employer_102_due_day": "15",
    },
    "2026-12": {
        # מוגש בינואר 2027 — לוודא עם פרסום לוח 2027 הרשמי
        "base_vat_periodic_and_income_tax_advances":      "2027-01-17",
        "effective_vat_periodic_and_income_tax_advances": "2027-01-17",
        "base_income_tax_withholding":      "2027-01-17",
        "effective_income_tax_withholding": "2027-01-17",
        "base_vat_detailed_pcn874":      "2027-01-23",
        "effective_vat_detailed_pcn874": "2027-01-24",
        "btl_employer_102_due_day": "15",
        "verification_note_he": "נגזר לפי כלל יום מנוחה; לאשר עם פרסום לוח 2027.",
    },
}

# מועד קבוע — ביטוח לאומי עצמאי: ה-15 בחודש, ללא לוח רשמי נפרד
BTL_MONTHLY_DUE_DAY = 15

# לוח מועדים שנתי — דוחות שנתיים על שנת מס 2026 (יוגשו ב-2027)
# יש לעדכן כשרשות המסים תפרסם לוח 2027 רשמי.
ANNUAL_TAX_AUTHORITY_DUE_DATES_2026: dict[str, dict[str, str]] = {
    "individual_1301": {
        "base_due_date": "2027-05-31",
        "effective_due_date": "2027-05-31",
        "form": "1301",
        "note_he": "מועד צפוי — טרם פורסמה דחייה רשמית לשנת מס 2026.",
    },
    "company_1214": {
        "base_due_date": "2027-07-31",
        "effective_due_date": "2027-07-31",
        "form": "1214",
        "note_he": "מועד צפוי — טרם פורסמה דחייה רשמית לשנת מס 2026.",
    },
    "osek_patur_annual_declaration": {
        "base_due_date": "2027-01-31",
        "effective_due_date": "2027-01-31",
        "form": "VAT_EXEMPT_DECLARATION",
        "note_he": "הצהרת מחזור שנתית לעוסק פטור עבור שנת 2026.",
    },
    # טופס 126 — דוח שנתי על ניכויים למעסיקים
    "withholding_126": {
        "base_due_date": "2027-04-30",
        "effective_due_date": "2027-04-30",
        "form": "126",
        "note_he": "דוח שנתי על ניכויים ממשכורות — מוגש עד 30/04 שלאחר שנת המס.",
    },
    # טופס 856 — דוח שנתי על תשלומים לתושבי חוץ
    "withholding_856": {
        "base_due_date": "2027-03-31",
        "effective_due_date": "2027-03-31",
        "form": "856",
        "note_he": "דוח שנתי על תשלומים לתושבי חוץ — מוגש עד 31/03 שלאחר שנת המס.",
    },
}
