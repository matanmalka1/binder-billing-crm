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


__all__ = ["SubmissionMethod", "VatType", "EntityType"]
