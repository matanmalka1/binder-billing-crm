"""Shared enumerations for annual income tax reports."""

from enum import Enum as PyEnum

from app.common.enums import SubmissionMethod


class AnnualReportType(str, PyEnum):
    """
    Filing profile of the main annual return for a client.

    The source-of-truth business rule is one main annual return per legal entity
    per tax year. ``report_type`` describes the filing profile, but is not meant
    to permit multiple primary annual returns for the same client and year.
    """
    INDIVIDUAL    = "individual"
    SELF_EMPLOYED = "self_employed"
    COMPANY       = "company"
    PUBLIC_INSTITUTION = "public_institution"
    EXEMPT_DEALER = "exempt_dealer"


class ClientTypeForReport(str, PyEnum):
    """Client types that determine which ITA form is required."""

    INDIVIDUAL = "individual"          # יחיד → form 1301
    SELF_EMPLOYED = "self_employed"    # עצמאי → form 1301 + נספח א'
    CORPORATION = "corporation"        # חברה → form 1214
    PUBLIC_INSTITUTION = "public_institution"  # מלכ"ר / מוסד ציבורי → form 1215
    PARTNERSHIP = "partnership"        # שותף בשותפות → usually form 1301 + 1504
    CONTROL_HOLDER = "control_holder"  # בעל שליטה → 1301 with company-like deadline
    EXEMPT_DEALER = "exempt_dealer"    # עוסק פטור / זעיר שחייב בדוח מלא; 0135 נשאר מחוץ לזרימת הדוח הראשי


class AnnualReportForm(str, PyEnum):
    """The ITA form number for the annual return."""

    FORM_0135 = "0135"  # Short refund request for taxpayers not required to file a full annual return
    FORM_1301 = "1301"  # Individual
    FORM_1214 = "1214"  # Company / cooperative
    FORM_1215 = "1215"  # Public institution / nonprofit (when relevant)
    FORM_6111 = "6111"  # Financial statement coding annex; not a primary return form


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
    SCHEDULE_A      = "schedule_a"       # 1320 — הכנסה מעסק או משלח יד
    SCHEDULE_B      = "schedule_b"       # 1321 — הכנסות מרכוש / עסקאות אקראיות
    SCHEDULE_GIMMEL = "schedule_gimmel"  # 1322 — רווח הון מניירות ערך סחירים
    SCHEDULE_DALET  = "schedule_dalet"   # 1324 — הכנסות מחו"ל ומס זר
    FORM_150        = "form_150"         # החזקה בחבר בני אדם תושב חוץ
    FORM_1504       = "form_1504"        # שותף בשותפות
    FORM_6111       = "form_6111"        # קידוד דוחות כספיים
    FORM_1344       = "form_1344"        # דיווח על הפסדים רלוונטיים
    FORM_1399       = "form_1399"        # הודעה על מכירת נכס ורווח הון
    FORM_1350       = "form_1350"        # משיכות בעל מניות מהותי
    FORM_1327       = "form_1327"        # דוח לנאמן בנאמנות
    FORM_1342       = "form_1342"        # פירוט נכסים שנתבע בגינם פחת
    FORM_1343       = "form_1343"        # ניכוי נוסף בשל פחת
    FORM_1348       = "form_1348"        # טענת אי-תושבות ישראל
    FORM_858        = "form_858"         # יחידות השתתפות בשותפות נפט

class FilingDeadlineType(str, PyEnum):
    STANDARD = "standard"   # Statutory by client type + submission channel
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
