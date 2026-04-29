from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Sequence


# ── Entity & classification enums ────────────────────────────────────────────

class EntityType(StrEnum):
    OSEK_PATUR  = "osek_patur"
    OSEK_MURSHE = "osek_murshe"
    COMPANY_LTD = "company_ltd"
    EMPLOYEE    = "employee"


class ReportingFrequency(StrEnum):
    MONTHLY    = "monthly"
    BIMONTHLY  = "bimonthly"
    ANNUAL     = "annual"
    NONE       = "none"


class BtlStatus(StrEnum):
    SELF_EMPLOYED     = "self_employed"
    EMPLOYEE          = "employee"
    NOT_SELF_EMPLOYED = "not_self_employed"
    UNKNOWN           = "unknown"


class Authority(StrEnum):
    VAT                 = "vat"
    INCOME_TAX          = "income_tax"
    NATIONAL_INSURANCE  = "national_insurance"
    WITHHOLDING         = "withholding"


class ObligationKind(StrEnum):
    VAT_PERIODIC_REPORT                     = "vat_periodic_report"
    VAT_DETAILED_REPORT_PCN874              = "vat_detailed_report_pcn874"
    VAT_EXEMPT_ANNUAL_DECLARATION           = "vat_exempt_annual_declaration"
    INCOME_TAX_ADVANCE                      = "income_tax_advance"
    INCOME_TAX_ANNUAL_REPORT                = "income_tax_annual_report"
    INCOME_TAX_ANNUAL_REPORT_SMALL_BUSINESS = "income_tax_annual_report_small_business"
    NATIONAL_INSURANCE_SELF_EMPLOYED_ADVANCE = "national_insurance_self_employed_advance"
    NATIONAL_INSURANCE_EMPLOYER_102         = "national_insurance_employer_102"
    WITHHOLDING_MONTHLY_102                 = "withholding_monthly_102"
    WITHHOLDING_ANNUAL_126                  = "withholding_annual_126"
    WITHHOLDING_ANNUAL_856                  = "withholding_annual_856"


class DueDateSourceKind(StrEnum):
    FIXED_DAY_NEXT_MONTH              = "fixed_day_next_month"
    OFFICIAL_YEARLY_CALENDAR          = "official_yearly_calendar"
    FIXED_DATE_AFTER_TAX_YEAR         = "fixed_date_after_tax_year"
    MANUAL_OR_REPRESENTATIVE_EXTENSION = "manual_or_representative_extension"


# ── Source reference ──────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SourceRef:
    id: str
    publisher: str
    title: str
    url: str
    checked_at: str
    note: str = ""


# ── Rule versioning ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RuleVersion:
    version: str          # e.g. "2026.1"
    effective_from: str   # ISO date "YYYY-MM-DD"
    effective_to: str | None
    verified_at: str      # ISO date — last human-verified against official source
    source_ids: tuple[str, ...]


# ── Due date policy ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class DuePolicy:
    kind: DueDateSourceKind
    statutory_day: int | None
    period_offset_months: int
    official_calendar_column: str | None = None
    description_he: str = ""


# ── Obligation scope (תחולה) ──────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ObligationScope:
    """
    Defines the conditions under which an obligation applies to a client.
    None = field not required / not checked.
    Empty tuple = obligation applies to all values of that field.
    """
    entity_types: tuple[EntityType, ...] = ()
    vat_frequencies: tuple[ReportingFrequency, ...] = ()
    advance_frequencies: tuple[ReportingFrequency, ...] = ()
    btl_statuses: tuple[BtlStatus, ...] = ()
    requires_pcn874: bool | None = None
    has_employees: bool | None = None
    has_withholding_file: bool | None = None
    has_representative: bool | None = None
    # ISO date strings — obligation applies only to clients opened before / not closed before
    opened_before: str | None = None
    closed_after: str | None = None


# ── Obligation rule ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ObligationRule:
    id: str
    authority: Authority
    kind: ObligationKind
    scope: ObligationScope
    frequency: ReportingFrequency
    due_policy: DuePolicy
    rule_version: RuleVersion
    label_he: str
    notes_he: tuple[str, ...] = ()
    not_applicable_reason_he: str | None = None


# ── Annual report rule ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AnnualReportRule:
    id: str
    scope: ObligationScope
    form: str
    is_attachment: bool           # True = נספח לדוח אחר (6111), לא דוח עצמאי
    default_due_month: int
    default_due_day: int
    tax_year_specific_due_dates: Mapping[int, str]   # {tax_year: "YYYY-MM-DD"}
    rule_version: RuleVersion
    label_he: str
    notes_he: tuple[str, ...] = ()


# ── Financial constants ───────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FinancialConstant:
    id: str
    year: int
    value: int | float | str
    unit: str
    effective_from: str
    effective_to: str | None
    source_ids: tuple[str, ...]
    note_he: str = ""


@dataclass(frozen=True, slots=True)
class RateBracket:
    up_to_ils: int | None   # None = אין תקרה (מדרגה עליונה)
    rate_percent: float
    label_he: str


@dataclass(frozen=True, slots=True)
class IncomeTaxBracket:
    """מדרגת מס הכנסה ליחיד — הכנסה מיגיעה אישית."""
    from_ils: int           # תחתית המדרגה (כולל)
    up_to_ils: int | None   # None = ללא תקרה (מדרגה עליונה)
    rate: float             # 0.0 – 1.0
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreditPointConfig:
    """נקודת זיכוי מס הכנסה — ערך בסיסי + נקודות ברירת מחדל לפרופילים נפוצים."""
    year: int
    monthly_value_ils: int      # שווי נקודה אחת לחודש
    annual_value_ils: int       # שווי נקודה אחת לשנה
    default_resident_points: float        # תושב ישראל זכר
    default_female_resident_points: float # תושבת ישראל נקבה
    source_ids: tuple[str, ...]


# ── VAT deduction rule ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class VatDeductionRule:
    category: str
    rate: float           # 0.0 – 1.0
    label_he: str
    condition_he: str = ""   # תנאי/הסבר (למשל: "רכב מסחרי בלבד")
    source_ids: tuple[str, ...] = ()


# ── Calendar override (דחייה/חריג) ────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class DeadlineOverride:
    period: str              # "YYYY-MM" or "YYYY" for annual
    column: str              # calendar column name
    original_date: str       # ISO date — base calendar date
    override_date: str       # ISO date — effective after override
    reason_he: str
    source_id: str


# ── Convenience alias ─────────────────────────────────────────────────────────

ClientTaxProfile = Mapping[str, str | int | bool | None]
