from __future__ import annotations

# לוח מועדים שנתי לשנת מס 2025 — מועדי הגשת דוחות שנתיים בלבד.
# (מועדי הדיווח התקופתי של 2025 אינם רלוונטיים לדוחות שהוגשו — הם היסטוריה.)
# המועדים כאן הם מועדי הגשת הדוחות השנתיים על הכנסות שנת 2025,
# שמוגשים בפועל במהלך 2026.
#
# מקורות:
#   - pa230426-1: דחיית המועד להגשת הדו״ח השנתי 2025 ליחידים וחברות
#   - sa240226-2: אורכה לעסק זעיר 2025

ANNUAL_TAX_AUTHORITY_DUE_DATES_2025: dict[str, dict[str, str]] = {
    # יחיד — טופס 1301
    "individual_1301": {
        "base_due_date": "2026-05-31",
        "effective_due_date": "2026-06-30",
        "form": "1301",
        "override_note_he": "דחייה חריגה לשנת מס 2025 — מועד מקורי 31/05/2026 נדחה ל-30/06/2026.",
        "source_id": "tax_authority_2025_annual_extension",
    },
    # חברה — טופס 1214
    "company_1214": {
        "base_due_date": "2026-07-31",
        "effective_due_date": "2026-07-30",
        "form": "1214",
        "override_note_he": "דחייה חריגה לשנת מס 2025 — 30/07/2026.",
        "source_id": "tax_authority_2025_annual_extension",
    },
    # עסק זעיר (יחיד עם מחזור עד תקרה) — מועד מיוחד
    "small_business": {
        "base_due_date": "2026-04-30",
        "effective_due_date": "2026-05-31",
        "form": "1301",
        "override_note_he": "אורכה לעסק זעיר לשנת מס 2025 — עד 31/05/2026.",
        "source_id": "tax_authority_small_business_2025_extension",
        "note_he": "עסק זעיר = יחיד שמחזורו מתחת לתקרה שנקבעת בכל שנה; יש לוודא תחולה.",
    },
    # עוסק פטור — הצהרת מחזור שנתית
    "osek_patur_annual_declaration": {
        "base_due_date": "2026-01-31",
        "effective_due_date": "2026-01-31",
        "form": "VAT_EXEMPT_DECLARATION",
        "note_he": "הצהרת מחזור שנתית לעוסק פטור עבור שנת 2025. לא דוח מע״מ תקופתי.",
        "source_id": "kolzchut_osek_patur",
    },
}
