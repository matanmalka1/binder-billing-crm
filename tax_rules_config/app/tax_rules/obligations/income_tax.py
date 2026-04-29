from __future__ import annotations

from ..types import (
    AnnualReportRule,
    Authority,
    DueDateSourceKind,
    DuePolicy,
    EntityType,
    ObligationKind,
    ObligationRule,
    ObligationScope,
    ReportingFrequency,
    RuleVersion,
)

_VERSION = RuleVersion(
    version="2026.1",
    effective_from="2026-01-01",
    effective_to=None,
    verified_at="2026-04-29",
    source_ids=("tax_authority_2026_calendar",),
)

_VERSION_ANNUAL = RuleVersion(
    version="2026.1",
    effective_from="2026-01-01",
    effective_to=None,
    verified_at="2026-04-29",
    source_ids=(
        "tax_authority_individual_2025_1301",
        "tax_authority_company_2025_1214",
        "tax_authority_2025_annual_extension",
        "kolzchut_annual_income_tax_report",
    ),
)

# ── מקדמות מס הכנסה ───────────────────────────────────────────────────────────
# תחולה: advance_frequencies קובע — לא entity_type בלבד.
# עוסק פטור יכול להיות חייב במקדמות; אל תגזור מ-VAT.

INCOME_TAX_ADVANCE_RULES: tuple[ObligationRule, ...] = (
    ObligationRule(
        id="income_tax.advance.osek_patur",
        authority=Authority.INCOME_TAX,
        kind=ObligationKind.INCOME_TAX_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR,),
            advance_frequencies=(ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="מקדמות מס הכנסה — עוסק פטור",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
            description_he="עוסק פטור אינו מדווח מע״מ — אבל יכול להיות חייב במקדמות מס הכנסה.",
        ),
        rule_version=_VERSION,
        notes_he=(
            "אל תגזור תדירות מקדמות מתדירות מע״מ.",
            "שמור income_tax_advance_frequency ו-income_tax_advance_rate בנפרד.",
        ),
    ),
    ObligationRule(
        id="income_tax.advance.osek_murshe",
        authority=Authority.INCOME_TAX,
        kind=ObligationKind.INCOME_TAX_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_MURSHE,),
            advance_frequencies=(ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="מקדמות מס הכנסה — עוסק מורשה",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
        ),
        rule_version=_VERSION,
    ),
    ObligationRule(
        id="income_tax.advance.company_ltd",
        authority=Authority.INCOME_TAX,
        kind=ObligationKind.INCOME_TAX_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.COMPANY_LTD,),
            advance_frequencies=(ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="מקדמות מס הכנסה — חברה בע״מ",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
        ),
        rule_version=_VERSION,
    ),
)

# ── דוחות שנתיים (legacy — ראה annual_reports.py לגרסה המלאה) ────────────────

ANNUAL_REPORT_RULES: tuple[AnnualReportRule, ...] = (
    AnnualReportRule(
        id="annual_report.individual.1301",
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE),
        ),
        form="1301",
        is_attachment=False,
        default_due_month=5,
        default_due_day=31,
        tax_year_specific_due_dates={2025: "2026-06-30"},
        rule_version=_VERSION_ANNUAL,
        label_he="דוח שנתי למס הכנסה ליחיד — טופס 1301",
        notes_he=(
            "ליחיד החייב בדוח מקוון לשנת 2025 — המועד עודכן ל-30.06.2026.",
            "למשרד מייצג יכולים להיות הסדרי אורכות נפרדים.",
        ),
    ),
    AnnualReportRule(
        id="annual_report.company.1214",
        scope=ObligationScope(
            entity_types=(EntityType.COMPANY_LTD,),
        ),
        form="1214",
        is_attachment=False,
        default_due_month=7,
        default_due_day=31,
        tax_year_specific_due_dates={2025: "2026-07-30"},
        rule_version=_VERSION_ANNUAL,
        label_he="דוח שנתי למס הכנסה לחברה — טופס 1214",
        notes_he=(
            "1214 = חברה; 1215 = מוסד ציבורי/מלכ״ר — לא לערבב.",
            "6111 הוא נספח אפשרי, לא דוח עצמאי.",
        ),
    ),
)

ANNUAL_REPORT_ATTACHMENTS: dict[str, dict] = {
    "6111": {
        "label_he": "נספח רווח והפסד/מאזן לדוח שנתי",
        "is_attachment": True,
        "source_ids": ("tax_authority_form_6111",),
        "notes_he": (
            "אל תציג 6111 כסוג דוח שנתי נפרד.",
            "החובה תלויה בתנאים/מחזור/סוג נישום.",
        ),
    },
}
