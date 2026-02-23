from datetime import datetime, timezone
from enum import Enum as PyEnum


class ClientTypeForReport(str, PyEnum):
    INDIVIDUAL = "individual"
    SELF_EMPLOYED = "self_employed"
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"


class AnnualReportForm(str, PyEnum):
    FORM_1301 = "1301"
    FORM_1215 = "1215"
    FORM_6111 = "6111"


class AnnualReportStatus(str, PyEnum):
    NOT_STARTED = "not_started"
    COLLECTING_DOCS = "collecting_docs"
    DOCS_COMPLETE = "docs_complete"
    IN_PREPARATION = "in_preparation"
    PENDING_CLIENT = "pending_client"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    ASSESSMENT_ISSUED = "assessment_issued"
    OBJECTION_FILED = "objection_filed"
    CLOSED = "closed"


class AnnualReportSchedule(str, PyEnum):
    SCHEDULE_B = "schedule_b"
    SCHEDULE_BET = "schedule_bet"
    SCHEDULE_GIMMEL = "schedule_gimmel"
    SCHEDULE_DALET = "schedule_dalet"
    SCHEDULE_HEH = "schedule_heh"


class DeadlineType(str, PyEnum):
    STANDARD = "standard"
    EXTENDED = "extended"
    CUSTOM = "custom"


FORM_MAP = {
    ClientTypeForReport.INDIVIDUAL: AnnualReportForm.FORM_1301,
    ClientTypeForReport.SELF_EMPLOYED: AnnualReportForm.FORM_1215,
    ClientTypeForReport.PARTNERSHIP: AnnualReportForm.FORM_1215,
    ClientTypeForReport.CORPORATION: AnnualReportForm.FORM_6111,
}

VALID_TRANSITIONS = {
    AnnualReportStatus.NOT_STARTED: {AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.COLLECTING_DOCS: {AnnualReportStatus.DOCS_COMPLETE, AnnualReportStatus.NOT_STARTED},
    AnnualReportStatus.DOCS_COMPLETE: {AnnualReportStatus.IN_PREPARATION, AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.IN_PREPARATION: {AnnualReportStatus.PENDING_CLIENT, AnnualReportStatus.DOCS_COMPLETE},
    AnnualReportStatus.PENDING_CLIENT: {AnnualReportStatus.IN_PREPARATION, AnnualReportStatus.SUBMITTED},
    AnnualReportStatus.SUBMITTED: {AnnualReportStatus.ACCEPTED, AnnualReportStatus.ASSESSMENT_ISSUED},
    AnnualReportStatus.ACCEPTED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.ASSESSMENT_ISSUED: {AnnualReportStatus.OBJECTION_FILED, AnnualReportStatus.CLOSED},
    AnnualReportStatus.OBJECTION_FILED: {AnnualReportStatus.CLOSED},
    AnnualReportStatus.CLOSED: set(),
}

SCHEDULE_FLAGS = [
    ("has_rental_income", AnnualReportSchedule.SCHEDULE_B),
    ("has_capital_gains", AnnualReportSchedule.SCHEDULE_BET),
    ("has_foreign_income", AnnualReportSchedule.SCHEDULE_GIMMEL),
    ("has_depreciation", AnnualReportSchedule.SCHEDULE_DALET),
    ("has_exempt_rental", AnnualReportSchedule.SCHEDULE_HEH),
]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def standard_deadline(tax_year: int):
    return datetime(tax_year + 1, 4, 30, 23, 59, 59)


def extended_deadline(tax_year: int):
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)

