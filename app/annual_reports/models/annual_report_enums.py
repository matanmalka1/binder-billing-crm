"""Shared enumerations for annual income tax reports."""

from enum import Enum as PyEnum

from app.common.enums import SubmissionMethod


class AnnualReportType(str, PyEnum):
    """
    Identity of the annual report — determines uniqueness per client+year.

    A single client (legal entity) can file multiple reports in the same tax year,
    one per report type. This is the discriminator used in the unique constraint.

    INDIVIDUAL    → Form 1301 (יחיד)
    SELF_EMPLOYED → Form 1215 (עצמאי / שותפות)
    COMPANY       → Form 6111 (חברה בע"מ)
    """
    INDIVIDUAL    = "individual"
    SELF_EMPLOYED = "self_employed"
    COMPANY       = "company"


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
    AMENDED = "amended"                     # דוח מתוקן
    ACCEPTED = "accepted"                   # התקבל / אושר
    ASSESSMENT_ISSUED = "assessment_issued" # שומה הוצאה
    OBJECTION_FILED = "objection_filed"     # השגה הוגשה
    CLOSED = "closed"                       # סגור


class AnnualReportSchedule(str, PyEnum):
    """Annexes / schedules that may be required alongside the main form."""
    SCHEDULE_B      = "schedule_b"       # שכירות
    SCHEDULE_BET    = "schedule_bet"     # רווחי הון
    SCHEDULE_GIMMEL = "schedule_gimmel"  # הכנסות מחו"ל
    SCHEDULE_DALET  = "schedule_dalet"   # פחת
    SCHEDULE_HEH    = "schedule_heh"     # שכר דירה פטור
    SCHEDULE_A      = "schedule_a"       # חישוב הכנסה מעסק
    SCHEDULE_VAV    = "schedule_vav"     # מכירת ניירות ערך
    ANNEX_15        = "annex_15"         # הכנסות מחו"ל מפורט
    ANNEX_867       = "annex_867"        # אישור בנקאי — נתונים כספיים

class FilingDeadlineType(str, PyEnum):
    STANDARD = "standard"   # April 30
    EXTENDED = "extended"   # January 31 following year (מייצגים)
    CUSTOM = "custom"       # ITA granted specific extension


class ReportStage(str, PyEnum):
    """
    Higher-level workflow stages used by dashboards.
    """

    MATERIAL_COLLECTION = "material_collection"
    IN_PROGRESS = "in_progress"
    FINAL_REVIEW = "final_review"
    CLIENT_SIGNATURE = "client_signature"
    TRANSMITTED = "transmitted"
    POST_SUBMISSION = "post_submission"  # assessment_issued, objection_filed

class ExtensionReason(str, PyEnum):
    MILITARY_SERVICE       = "military_service"  # מילואים
    HEALTH_REASON          = "health_reason"     # סיבה רפואית
    GENERAL_REPRESENTATIVE = "general"           # הארכה כללית של המייצג
    WAR_SITUATION          = "war_situation"     # מצב ביטחוני

ANNUAL_REPORT_FILED_STATUSES: frozenset[AnnualReportStatus] = frozenset({
    AnnualReportStatus.SUBMITTED,
    AnnualReportStatus.ACCEPTED,
    AnnualReportStatus.ASSESSMENT_ISSUED,
    AnnualReportStatus.OBJECTION_FILED,
    AnnualReportStatus.CLOSED,
})

__all__ = [
    "ANNUAL_REPORT_FILED_STATUSES",
    "AnnualReportForm",
    "AnnualReportSchedule",
    "AnnualReportStatus",
    "AnnualReportType",
    "ClientTypeForReport",
    "FilingDeadlineType",
    "ExtensionReason",
    "ReportStage",
    "SubmissionMethod",
]
