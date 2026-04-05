from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
)
from app.annual_reports.models.annual_report_expense_line import (
    DEFAULT_RECOGNITION_RATE,
    STATUTORY_RECOGNITION_RATES,
)

# Which form each client type must use
FORM_MAP: dict[ClientTypeForReport, AnnualReportForm] = {
    ClientTypeForReport.INDIVIDUAL: AnnualReportForm.FORM_1301,
    ClientTypeForReport.SELF_EMPLOYED: AnnualReportForm.FORM_1215,
    ClientTypeForReport.PARTNERSHIP: AnnualReportForm.FORM_1215,
    ClientTypeForReport.CORPORATION: AnnualReportForm.FORM_6111,
}

# Valid status transitions (from → set of allowed next statuses)
VALID_TRANSITIONS: dict[AnnualReportStatus, set[AnnualReportStatus]] = {
    AnnualReportStatus.NOT_STARTED: {AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.COLLECTING_DOCS: {
        AnnualReportStatus.DOCS_COMPLETE,
        AnnualReportStatus.NOT_STARTED,
    },
    AnnualReportStatus.DOCS_COMPLETE: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.COLLECTING_DOCS,
    },
    AnnualReportStatus.IN_PREPARATION: {
        AnnualReportStatus.PENDING_CLIENT,
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.PENDING_CLIENT: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.SUBMITTED,
    },
    AnnualReportStatus.SUBMITTED: {
        AnnualReportStatus.ACCEPTED,
        AnnualReportStatus.ASSESSMENT_ISSUED,
    },
    AnnualReportStatus.AMENDED: {
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.SUBMITTED,
    },
    AnnualReportStatus.ACCEPTED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.ASSESSMENT_ISSUED: {
        AnnualReportStatus.OBJECTION_FILED,
        AnnualReportStatus.CLOSED,
        # Allow operational rollback when issues found post-assessment
        AnnualReportStatus.PENDING_CLIENT,
        AnnualReportStatus.IN_PREPARATION,
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.OBJECTION_FILED: {
        AnnualReportStatus.CLOSED,
        # Permit rollback to rework documents if objection rejected/updated
        AnnualReportStatus.DOCS_COMPLETE,
    },
    AnnualReportStatus.CLOSED: set(),
}

# ── Kanban stage → status mapping (one-way: promotes to first status in stage) ──
# Note: this map intentionally moves to a single target status per stage.
# Demoting within a stage requires direct status transition.
STAGE_TO_STATUS: dict[str, str] = {
    "material_collection": "collecting_docs",
    "in_progress": "docs_complete",
    "final_review": "in_preparation",
    "client_signature": "pending_client",
    "transmitted": "submitted",
}

# ── Israeli tax law constants ──────────────────────────────────────────────────
# Donation credit rate — Section 46 of the Income Tax Ordinance
DONATION_CREDIT_RATE = 0.35

# ── National Insurance (ביטוח לאומי) rates — per NII annual circular ──────────
# Base rate applies up to the monthly ceiling; high rate applies above it
NI_RATE_BASE = 0.0597
NI_RATE_HIGH = 0.1783

# ── Statutory partial recognition rates — Income Tax Regulations ──────────────
# Vehicle (Reg. 28): 75% deductible; Telephone/communication (Reg. 22): 80%
# ── Stuck-report defaults ──────────────────────────────────────────────────────
STUCK_REPORT_STALE_DAYS = 7
STUCK_REPORT_LIMIT = 3

# Which schedules are triggered by income flags
SCHEDULE_FLAGS = [
    ("has_rental_income", AnnualReportSchedule.SCHEDULE_B),
    ("has_capital_gains", AnnualReportSchedule.SCHEDULE_BET),
    ("has_foreign_income", AnnualReportSchedule.SCHEDULE_GIMMEL),
    ("has_depreciation", AnnualReportSchedule.SCHEDULE_DALET),
    ("has_exempt_rental", AnnualReportSchedule.SCHEDULE_HEH),
]

__all__ = [
    "DEFAULT_RECOGNITION_RATE",
    "DONATION_CREDIT_RATE",
    "FORM_MAP",
    "NI_RATE_BASE",
    "NI_RATE_HIGH",
    "SCHEDULE_FLAGS",
    "STAGE_TO_STATUS",
    "STATUTORY_RECOGNITION_RATES",
    "STUCK_REPORT_STALE_DAYS",
    "STUCK_REPORT_LIMIT",
    "VALID_TRANSITIONS",
]
