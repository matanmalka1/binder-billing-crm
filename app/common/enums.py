"""Shared enums used across multiple business domains."""

from enum import Enum as PyEnum


class SubmissionMethod(str, PyEnum):
    ONLINE = "online"  # שידור ישיר (מייצגים)
    MANUAL = "manual"  # הגשה פיזית לפקיד השומה
    REPRESENTATIVE = "representative"  # דרך מערכת המייצגים (שע"מ)


class VatType(str, PyEnum):
    """VAT reporting frequency for a legal entity (Client level)."""
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    EXEMPT = "exempt"


class EntityType(str, PyEnum):
    """
    The legal/tax classification of a Client (legal entity).

    OSEK_PATUR  — עוסק פטור: exempt from VAT collection; annual reporting only.
    OSEK_MURSHE — עוסק מורשה: collects/deducts VAT; monthly or bi-monthly reporting.
    COMPANY_LTD — חברה בע"מ: separate legal entity with its own ח"פ; monthly/bi-monthly.
    EMPLOYEE    — שכיר: wage earner; no VAT reporting.
    """
    OSEK_PATUR  = "osek_patur"
    OSEK_MURSHE = "osek_murshe"
    COMPANY_LTD = "company_ltd"
    EMPLOYEE    = "employee"


class IdNumberType(str, PyEnum):
    INDIVIDUAL  = "individual"   # ת"ז — 9 ספרות עם ספרת ביקורת
    CORPORATION = "corporation"  # ח"פ — 9 ספרות
    PASSPORT    = "passport"     # דרכון — לתושבי חוץ
    OTHER       = "other"


class AdvancePaymentFrequency(str, PyEnum):
    """Advance payment reporting frequency — independent from VAT frequency."""
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"


class ObligationType(str, PyEnum):
    """Regulatory obligation category for TaxCalendarEntry.

    NATIONAL_INSURANCE is reserved but not yet wired to a DeadlineRuleType
    (intentionally unsupported in PR 1 of the tax-calendar foundation).
    """
    VAT                = "vat"
    ADVANCE_PAYMENT    = "advance_payment"
    ANNUAL_REPORT      = "annual_report"
    NATIONAL_INSURANCE = "national_insurance"


class DeadlineRuleType(str, PyEnum):
    """Regulatory rule variant. Maps to one ObligationType."""
    VAT_MONTHLY        = "vat_monthly"
    VAT_BIMONTHLY      = "vat_bimonthly"
    ADVANCE_MONTHLY    = "advance_monthly"
    ADVANCE_BIMONTHLY  = "advance_bimonthly"
    ANNUAL_REPORT      = "annual_report"


__all__ = [
    "AdvancePaymentFrequency",
    "DeadlineRuleType",
    "EntityType",
    "IdNumberType",
    "ObligationType",
    "SubmissionMethod",
    "VatType",
]
