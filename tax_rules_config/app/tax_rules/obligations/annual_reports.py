from __future__ import annotations

from ..types import (
    AnnualReportRule,
    EntityType,
    ObligationScope,
    RuleVersion,
)

_VERSION = RuleVersion(
    version="2026.1",
    effective_from="2026-01-01",
    effective_to=None,
    verified_at="2026-04-29",
    source_ids=(
        "tax_authority_individual_2025_1301",
        "tax_authority_company_2025_1214",
        "tax_authority_2025_annual_extension",
        "tax_authority_small_business_2025_extension",
        "kolzchut_annual_income_tax_report",
        "tax_authority_form_6111",
    ),
)

# ── דוחות שנתיים — גרסה מלאה ─────────────────────────────────────────────────

ANNUAL_REPORT_RULES_V2: tuple[AnnualReportRule, ...] = (
    # ── יחיד — טופס 1301 ─────────────────────────────────────────────────────
    AnnualReportRule(
        id="annual_report.individual.1301",
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE),
        ),
        form="1301",
        is_attachment=False,
        default_due_month=5,
        default_due_day=31,
        tax_year_specific_due_dates={
            2025: "2026-06-30",  # דחייה חריגה — pa230426-1
        },
        rule_version=_VERSION,
        label_he="דוח שנתי למס הכנסה ליחיד — טופס 1301",
        notes_he=(
            "חובה להגיש לכל מי שהכנסתו חייבת בהגשת דוח (בהתאם לתקנות).",
            "ליחיד שמייצג אותו רו״ח — ייתכנו אורכות נפרדות.",
            "לשנת 2025: המועד עודכן ל-30.06.2026 (דחייה חריגה רשמית).",
        ),
    ),
    # ── עסק זעיר — דוח פשוט / טופס 1301 מקוצר ──────────────────────────────
    AnnualReportRule(
        id="annual_report.small_business.1301_simplified",
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE),
        ),
        form="1301",
        is_attachment=False,
        default_due_month=4,
        default_due_day=30,
        tax_year_specific_due_dates={
            2025: "2026-05-31",  # אורכה לעסק זעיר — sa240226-2
        },
        rule_version=_VERSION,
        label_he="דוח שנתי — עסק זעיר (מועד מוקדם)",
        notes_he=(
            "עסק זעיר = יחיד שמחזורו מתחת לתקרה שנקבעת מדי שנה על ידי רשות המסים.",
            "לשנת 2025: אורכה עד 31/05/2026.",
            "יש לוודא תחולה לפי מחזור בפועל — לא לפי שדה סטטי.",
            "אין ליצור חובה זו בנוסף ל-1301 הרגיל — רק אחד מהם חל.",
        ),
    ),
    # ── חברה — טופס 1214 ─────────────────────────────────────────────────────
    AnnualReportRule(
        id="annual_report.company.1214",
        scope=ObligationScope(
            entity_types=(EntityType.COMPANY_LTD,),
        ),
        form="1214",
        is_attachment=False,
        default_due_month=7,
        default_due_day=31,
        tax_year_specific_due_dates={
            2025: "2026-07-30",  # דחייה חריגה — pa230426-1
        },
        rule_version=_VERSION,
        label_he="דוח שנתי למס הכנסה לחברה — טופס 1214",
        notes_he=(
            "1214 = חברה רגילה בע״מ.",
            "1215 = מוסד ציבורי/מלכ״ר — לא לערבב.",
            "6111 הוא נספח אפשרי לדוח — לא דוח עצמאי.",
            "לשנת 2025: המועד עודכן ל-30.07.2026.",
        ),
    ),
    # ── 6111 — נספח לדוח שנתי (לא דוח עצמאי) ────────────────────────────────
    AnnualReportRule(
        id="annual_report.attachment.6111",
        scope=ObligationScope(
            entity_types=(
                EntityType.OSEK_MURSHE,
                EntityType.COMPANY_LTD,
            ),
        ),
        form="6111",
        is_attachment=True,
        default_due_month=0,   # 0 = תלוי בדוח השנתי האב
        default_due_day=0,
        tax_year_specific_due_dates={},
        rule_version=_VERSION,
        label_he="נספח 6111 — פירוט רווח והפסד/מאזן לדוח שנתי",
        notes_he=(
            "6111 הוא נספח לדוח השנתי — אין לו מועד עצמאי.",
            "החובה תלויה בסוג הנישום, מחזור, וחובה פרטנית מרשות המסים.",
            "שמור שדה requires_form_6111 על הלקוח.",
        ),
    ),
)
