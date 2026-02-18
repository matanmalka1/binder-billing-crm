from app.annual_reports.models import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
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
    AnnualReportStatus.ACCEPTED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.ASSESSMENT_ISSUED: {
        AnnualReportStatus.OBJECTION_FILED,
        AnnualReportStatus.CLOSED,
    },
    AnnualReportStatus.OBJECTION_FILED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.CLOSED: set(),
}

# Which schedules are triggered by income flags
SCHEDULE_FLAGS = [
    ("has_rental_income", AnnualReportSchedule.SCHEDULE_B),
    ("has_capital_gains", AnnualReportSchedule.SCHEDULE_BET),
    ("has_foreign_income", AnnualReportSchedule.SCHEDULE_GIMMEL),
    ("has_depreciation", AnnualReportSchedule.SCHEDULE_DALET),
    ("has_exempt_rental", AnnualReportSchedule.SCHEDULE_HEH),
]

__all__ = [
    "FORM_MAP",
    "SCHEDULE_FLAGS",
    "VALID_TRANSITIONS",
]
