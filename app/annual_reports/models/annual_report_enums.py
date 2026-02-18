"""Shared enumerations for annual income tax reports."""

from enum import Enum as PyEnum


class ClientTypeForReport(str, PyEnum):
    """Client types that determine which ITA form is required."""

    INDIVIDUAL = "individual"          # יחיד → form 1301
    SELF_EMPLOYED = "self_employed"    # עצמאי → form 1215
    CORPORATION = "corporation"        # חברה → form 6111
    PARTNERSHIP = "partnership"        # שותפות → form 1215 variant


class AnnualReportForm(str, PyEnum):
    """The ITA form number for the annual return."""

    FORM_1301 = "1301"  # Individual
    FORM_1215 = "1215"  # Self-employed / partnership
    FORM_6111 = "6111"  # Corporation


class AnnualReportStatus(str, PyEnum):
    NOT_STARTED = "not_started"
    COLLECTING_DOCS = "collecting_docs"     # מאסף מסמכים
    DOCS_COMPLETE = "docs_complete"         # מסמכים התקבלו
    IN_PREPARATION = "in_preparation"       # בהכנה
    PENDING_CLIENT = "pending_client"       # ממתין לאישור לקוח
    SUBMITTED = "submitted"                 # הוגש לרשות המסים
    ACCEPTED = "accepted"                   # התקבל / אושר
    ASSESSMENT_ISSUED = "assessment_issued" # שומה הוצאה
    OBJECTION_FILED = "objection_filed"     # השגה הוגשה
    CLOSED = "closed"                       # סגור


class AnnualReportSchedule(str, PyEnum):
    """Annexes / schedules that may be required alongside the main form."""

    SCHEDULE_B = "schedule_b"          # נספח ב — שכירות
    SCHEDULE_BET = "schedule_bet"      # נספח בית — רווחי הון
    SCHEDULE_GIMMEL = "schedule_gimmel" # נספח ג — הכנסות מחו\"ל
    SCHEDULE_DALET = "schedule_dalet"  # נספח ד — פחת
    SCHEDULE_HEH = "schedule_heh"      # נספח ה — שכר דירה פטור


class DeadlineType(str, PyEnum):
    STANDARD = "standard"   # April 30
    EXTENDED = "extended"   # January 31 following year (מייצגים)
    CUSTOM = "custom"       # ITA granted specific extension


class ReportStage(str, PyEnum):
    """
    Higher-level workflow stages used by dashboards.
    (Implemented per Sprint 7/8 specifications.)
    """

    MATERIAL_COLLECTION = "material_collection"
    IN_PROGRESS = "in_progress"
    FINAL_REVIEW = "final_review"
    CLIENT_SIGNATURE = "client_signature"
    TRANSMITTED = "transmitted"


__all__ = [
    "AnnualReportForm",
    "AnnualReportSchedule",
    "AnnualReportStatus",
    "ClientTypeForReport",
    "DeadlineType",
    "ReportStage",
]
