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
    source_ids=(
        "btl_self_employed_payment_due",
        "btl_self_employed_rates_2026",
        "btl_employer_102_due",
        "btl_2026_constants_circular",
    ),
)

NATIONAL_INSURANCE_RULES: tuple[ObligationRule, ...] = (
    # ── עצמאי — עוסק פטור ────────────────────────────────────────────────────
    ObligationRule(
        id="btl.self_employed.osek_patur",
        authority=Authority.NATIONAL_INSURANCE,
        kind=ObligationKind.NATIONAL_INSURANCE_SELF_EMPLOYED_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_PATUR,),
            btl_statuses=(BtlStatus.SELF_EMPLOYED,),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="מקדמת ביטוח לאומי — עצמאי / עוסק פטור",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DAY_NEXT_MONTH,
            statutory_day=15,
            period_offset_months=1,
            description_he="עד ה-15 בחודש עבור החודש הקודם.",
        ),
        rule_version=_VERSION,
        notes_he=(
            "עוסק פטור/מורשה = סיווג מע״מ; בב״ל הסיווג המרכזי הוא עצמאי/לא עצמאי.",
            "ב״ל לעצמאי הוא תמיד חודשי — אין דו-חודשי.",
        ),
    ),
    # ── עצמאי — עוסק מורשה ───────────────────────────────────────────────────
    ObligationRule(
        id="btl.self_employed.osek_murshe",
        authority=Authority.NATIONAL_INSURANCE,
        kind=ObligationKind.NATIONAL_INSURANCE_SELF_EMPLOYED_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.OSEK_MURSHE,),
            btl_statuses=(BtlStatus.SELF_EMPLOYED,),
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="מקדמת ביטוח לאומי — עצמאי / עוסק מורשה",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DAY_NEXT_MONTH,
            statutory_day=15,
            period_offset_months=1,
            description_he="עד ה-15 בחודש עבור החודש הקודם.",
        ),
        rule_version=_VERSION,
    ),
    # ── חברה בע"מ — לא חייבת כעצמאי ─────────────────────────────────────────
    ObligationRule(
        id="btl.company_ltd.not_self_employed",
        authority=Authority.NATIONAL_INSURANCE,
        kind=ObligationKind.NATIONAL_INSURANCE_SELF_EMPLOYED_ADVANCE,
        scope=ObligationScope(
            entity_types=(EntityType.COMPANY_LTD,),
        ),
        frequency=ReportingFrequency.NONE,
        label_he="ביטוח לאומי חברה בע״מ — לא חל ברמת החברה כעצמאי",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DAY_NEXT_MONTH,
            statutory_day=None,
            period_offset_months=0,
            description_he="חברה אינה משלמת מקדמות ב״ל כעצמאי.",
        ),
        rule_version=_VERSION,
        not_applicable_reason_he=(
            "אין מקדמות ב״ל לעצמאי עבור חברה בע״מ. "
            "בדוק חובת מעסיק/שכר בעלי שליטה בנפרד."
        ),
    ),
    # ── מעסיק — טופס 102 (לכל סוגי ישות עם עובדים) ──────────────────────────
    ObligationRule(
        id="btl.employer_102",
        authority=Authority.NATIONAL_INSURANCE,
        kind=ObligationKind.NATIONAL_INSURANCE_EMPLOYER_102,
        scope=ObligationScope(
            entity_types=(
                EntityType.COMPANY_LTD,
                EntityType.OSEK_MURSHE,
                EntityType.OSEK_PATUR,
            ),
            has_employees=True,
        ),
        frequency=ReportingFrequency.MONTHLY,
        label_he="דיווח ותשלום ביטוח לאומי כמעסיק — טופס 102",
        due_policy=DuePolicy(
            kind=DueDateSourceKind.FIXED_DAY_NEXT_MONTH,
            statutory_day=15,
            period_offset_months=1,
            description_he="עד ה-15 בחודש עבור החודש הקודם.",
        ),
        rule_version=_VERSION,
        notes_he=("החובה תלויה בקיום עובדים/שכר — לא רק בסוג הישות.",),
    ),
)
