from __future__ import annotations

from ..types import (
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

WITHHOLDING_RULES: tuple[ObligationRule, ...] = (
    # ── ניכוי במקור חודשי — טופס 102 מס הכנסה ───────────────────────────────
    # חובה: כל מעסיק שמנכה מס מעובדים/ספקים.
    # תחולה: has_withholding_file=True
    ObligationRule(
        id="withholding.monthly_102.income_tax",
        authority=Authority.WITHHOLDING,
        kind=ObligationKind.WITHHOLDING_MONTHLY_102,
        scope=ObligationScope(
            entity_types=(
                EntityType.COMPANY_LTD,
                EntityType.OSEK_MURSHE,
                EntityType.OSEK_PATUR,
            ),
            has_withholding_file=True,
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="ניכוי במקור חודשי — טופס 102 מס הכנסה",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.OFFICIAL_YEARLY_CALENDAR,
            statutory_day=15,
            period_offset_months=1,
            official_calendar_column="effective_income_tax_withholding",
            description_he="עד ה-15 בחודש שלאחר חודש הניכוי; בפועל לפי לוח רשמי שנתי.",
        ),
        rule_version=_VERSION,
        notes_he=(
            "תחולה: למי שקיים תיק ניכויים פתוח ברשות המסים.",
            "כולל ניכוי ממשכורות, שכ״ד, שירותים, קבלנים עצמאיים.",
        ),
    ),
    # ── דוח שנתי ניכויים — טופס 126 ─────────────────────────────────────────
    # מוגש פעם בשנה עבור כל שנת המס — דוח מסכם על ניכויים ממשכורות.
    ObligationRule(
        id="withholding.annual_126",
        authority=Authority.WITHHOLDING,
        kind=ObligationKind.WITHHOLDING_ANNUAL_126,
        scope=ObligationScope(
            entity_types=(
                EntityType.COMPANY_LTD,
                EntityType.OSEK_MURSHE,
                EntityType.OSEK_PATUR,
            ),
            has_withholding_file=True,
            has_employees=True,
        ),
        frequency=ReportingFrequency.ANNUAL,
        label_he="דוח שנתי על ניכויים ממשכורות — טופס 126",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DATE_AFTER_TAX_YEAR,
            statutory_day=30,
            period_offset_months=4,
            description_he="מוגש עד 30/04 שלאחר שנת המס (למשל: טופס 126 לשנת 2026 מוגש עד 30/04/2027).",
        ),
        rule_version=_VERSION,
        notes_he=(
            "כולל פירוט לכל עובד (שם, ת״ז, הכנסה, ניכוי, נקודות זיכוי).",
            "הגשה אלקטרונית חובה ברוב המקרים.",
        ),
    ),
    # ── דוח שנתי על תשלומים לתושבי חוץ — טופס 856 ───────────────────────────
    # חובה: מי ששילם לתושב חוץ ועליו לנכות מס במקור.
    ObligationRule(
        id="withholding.annual_856",
        authority=Authority.WITHHOLDING,
        kind=ObligationKind.WITHHOLDING_ANNUAL_856,
        scope=ObligationScope(
            entity_types=(
                EntityType.COMPANY_LTD,
                EntityType.OSEK_MURSHE,
                EntityType.OSEK_PATUR,
            ),
            has_withholding_file=True,
        ),
        frequency=ReportingFrequency.ANNUAL,
        label_he="דוח שנתי על תשלומים לתושבי חוץ — טופס 856",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DATE_AFTER_TAX_YEAR,
            statutory_day=31,
            period_offset_months=3,
            description_he="מוגש עד 31/03 שלאחר שנת המס (למשל: טופס 856 לשנת 2026 מוגש עד 31/03/2027).",
        ),
        rule_version=_VERSION,
        notes_he=(
            "חובה רק אם שולמו תשלומים לתושבי חוץ בשנת המס.",
            "יש לוודא תחולה לפי קיום תשלומים בפועל — לא לפי שדה סטטי בלבד.",
        ),
    ),
)
