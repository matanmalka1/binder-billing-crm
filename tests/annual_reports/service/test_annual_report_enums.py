from datetime import datetime
from enum import Enum as PyEnum

from app.utils.time_utils import utcnow


class ClientTypeForReport(str, PyEnum):
    INDIVIDUAL = "individual"
    SELF_EMPLOYED = "self_employed"
    CORPORATION = "corporation"
    PUBLIC_INSTITUTION = "public_institution"
    PARTNERSHIP = "partnership"
    CONTROL_HOLDER = "control_holder"
    EXEMPT_DEALER = "exempt_dealer"


class AnnualReportType(str, PyEnum):
    INDIVIDUAL = "individual"
    SELF_EMPLOYED = "self_employed"
    COMPANY = "company"
    PUBLIC_INSTITUTION = "public_institution"
    EXEMPT_DEALER = "exempt_dealer"


class AnnualReportForm(str, PyEnum):
    FORM_0135 = "0135"
    FORM_1301 = "1301"
    FORM_1214 = "1214"
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
    SCHEDULE_A = "schedule_a"
    SCHEDULE_B = "schedule_b"
    SCHEDULE_GIMMEL = "schedule_gimmel"
    SCHEDULE_DALET = "schedule_dalet"
    FORM_150 = "form_150"
    FORM_1504 = "form_1504"
    FORM_6111 = "form_6111"
    FORM_1344 = "form_1344"
    FORM_1399 = "form_1399"
    FORM_1350 = "form_1350"
    FORM_1327 = "form_1327"
    FORM_1342 = "form_1342"
    FORM_1343 = "form_1343"
    FORM_1348 = "form_1348"
    FORM_858 = "form_858"


class DeadlineType(str, PyEnum):
    STANDARD = "standard"
    EXTENDED = "extended"
    CUSTOM = "custom"


FORM_MAP = {
    ClientTypeForReport.INDIVIDUAL: AnnualReportForm.FORM_1301,
    ClientTypeForReport.SELF_EMPLOYED: AnnualReportForm.FORM_1301,
    ClientTypeForReport.PARTNERSHIP: AnnualReportForm.FORM_1301,
    ClientTypeForReport.CONTROL_HOLDER: AnnualReportForm.FORM_1301,
    ClientTypeForReport.CORPORATION: AnnualReportForm.FORM_1214,
    ClientTypeForReport.PUBLIC_INSTITUTION: AnnualReportForm.FORM_1215,
    ClientTypeForReport.EXEMPT_DEALER: AnnualReportForm.FORM_0135,
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
    ("has_capital_gains", AnnualReportSchedule.SCHEDULE_GIMMEL),
    ("has_foreign_income", AnnualReportSchedule.SCHEDULE_DALET),
]


def standard_deadline(tax_year: int, client_type=None, submission_method=None):
    if client_type in {ClientTypeForReport.CORPORATION, ClientTypeForReport.PUBLIC_INSTITUTION, ClientTypeForReport.CONTROL_HOLDER}:
        return datetime(tax_year + 1, 7, 31, 23, 59, 59)
    if submission_method in {"online", "representative"}:
        return datetime(tax_year + 1, 6, 30, 23, 59, 59)
    return datetime(tax_year + 1, 5, 29, 23, 59, 59)


def extended_deadline(tax_year: int):
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)
