from __future__ import annotations

from ..types import (
    Authority,
    BtlStatus,
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
    source_ids=("tax_authority_2026_calendar", "tax_authority_vat_amounts_2026"),
)

VAT_RULES: tuple[ObligationRule, ...] = (
    # ── עוסק מורשה — דיווח חודשי ─────────────────────────────────────────────
    ObligationRule(
        id="vat.periodic.osek_murshe.monthly",
        authority=Authority.VAT,
        kind=ObligationKind.VAT_PERIODIC_REPORT,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_MURSHE,),
            vat_frequencies=(ReportingFrequency.MONTHLY,),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="דיווח ותשלום מע״מ — עוסק מורשה חודשי",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
            description_he="מועד בסיסי ה-15; בפועל לפי לוח רשמי שנתי.",
        ),
        rule_version=_VERSION,
    ),
    # ── עוסק מורשה — דיווח דו-חודשי ─────────────────────────────────────────
    ObligationRule(
        id="vat.periodic.osek_murshe.bimonthly",
        authority=Authority.VAT,
        kind=ObligationKind.VAT_PERIODIC_REPORT,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_MURSHE,),
            vat_frequencies=(ReportingFrequency.BIMONTHLY,),
        ),
        frequency=ReportingFrequency.BIMONTHLY,
        label_he="דיווח ותשלום מע״מ — עוסק מורשה דו-חודשי",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
            description_he="מפתח לוח: החודש השני של התקופה (ינואר-פברואר => 2026-02).",
        ),
        rule_version=_VERSION,
    ),
    # ── חברה בע"מ — דיווח חודשי או דו-חודשי ─────────────────────────────────
    ObligationRule(
        id="vat.periodic.company_ltd.monthly_or_bimonthly",
        authority=Authority.VAT,
        kind=ObligationKind.VAT_PERIODIC_REPORT,
        scope=ObligationScope(
            entity_types=(EntityType.COMPANY_LTD,),
            vat_frequencies=(ReportingFrequency.MONTHLY, ReportingFrequency.BIMONTHLY),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="דיווח ותשלום מע״מ — חברה בע״מ",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_vat_periodic_and_income_tax_advances",
            description_he="תדירות בפועל לפי שדה vat_reporting_frequency בתיק.",
        ),
        rule_version=_VERSION,
        notes_he=("אל תניח שכל חברה חודשית — שמור תדירות מהתיק.",),
    ),
    # ── עוסק פטור — הצהרת מחזור שנתית ───────────────────────────────────────
    ObligationRule(
        id="vat.annual_declaration.osek_patur",
        authority=Authority.VAT,
        kind=ObligationKind.VAT_EXEMPT_ANNUAL_DECLARATION,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR,),
        ),
        frequency=ReportingFrequency.ANNUAL,
        label_he="הצהרת מחזור שנתית למע״מ — עוסק פטור",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DATE_AFTER_TAX_YEAR,
            statutory_day=31,
            period_offset_months=1,
            description_he="עד 31 בינואר שלאחר שנת המס, בכפוף לדחיות רשמיות.",
        ),
        rule_version=_VERSION,
        notes_he=(
            "אין ליצור לעוסק פטור דוחות מע״מ חודשיים/דו-חודשיים.",
            "חריגה מתקרת המחזור מחייבת טיפול ידני — לא רק תזכורת.",
        ),
    ),
    # ── PCN874 — דוח מפורט ───────────────────────────────────────────────────
    ObligationRule(
        id="vat.detailed.pcn874",
        authority=Authority.VAT,
        kind=ObligationKind.VAT_DETAILED_REPORT_PCN874,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_MURSHE, EntityType.COMPANY_LTD),
            requires_pcn874=True,
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="דוח מע״מ מפורט PCN874",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=23,
            period_offset_months=1,
            official_calendar_column="effective_vat_detailed_pcn874",
            description_he="מועד בסיסי ה-23; בפועל לפי לוח רשמי שנתי.",
        ),
        rule_version=_VERSION,
        notes_he=(
            "לא כל עוסק מורשה חייב PCN874 — תלוי בספי מחזור/חובה פרטנית.",
            "שמור שדה requires_pcn874 על הלקוח.",
        ),
    ),
)
