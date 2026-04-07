"""Shared enums used across multiple business domains."""

from enum import Enum as PyEnum


class SubmissionMethod(str, PyEnum):
    ONLINE = "online"  # שידור ישיר (מייצגים)
    MANUAL = "manual"  # הגשה פיזית לפקיד השומה
    REPRESENTATIVE = "representative"  # דרך מערכת המייצגים (שע"מ)


class VatType(str, PyEnum):
    """
    VAT reporting frequency for a legal entity.

    For OSEK_MURSHE businesses: authoritative value lives on Client.vat_reporting_frequency.
    For COMPANY businesses: authoritative value lives on BusinessTaxProfile.vat_type.
    BusinessTaxProfile.vat_type is DEPRECATED for OSEK_MURSHE — do not read it for period resolution.
    """
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    EXEMPT = "exempt"


__all__ = ["SubmissionMethod", "VatType"]
