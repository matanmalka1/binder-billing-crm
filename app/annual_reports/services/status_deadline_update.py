"""Deadline update helper for annual reports."""

from app.annual_reports.models.annual_report_enums import FilingDeadlineType
from app.core.exceptions import AppError

from .deadlines import extended_deadline, standard_deadline
from .messages import CUSTOM_DEADLINE_LABEL, DEADLINE_UPDATED_NOTE, INVALID_DEADLINE_TYPE_ERROR


def update_report_deadline(service, report_id: int, deadline_type: str, changed_by: int, custom_deadline_note=None):
    report = service._get_or_raise_for_update(report_id)
    valid_deadline_types = {e.value for e in FilingDeadlineType}
    if deadline_type not in valid_deadline_types:
        raise AppError(INVALID_DEADLINE_TYPE_ERROR.format(deadline_type=deadline_type), "ANNUAL_REPORT.INVALID_TYPE")
    dt = FilingDeadlineType(deadline_type)
    if dt == FilingDeadlineType.STANDARD:
        filing_deadline = standard_deadline(
            report.tax_year,
            client_type=report.client_type,
            submission_method=report.submission_method,
        )
    elif dt == FilingDeadlineType.EXTENDED:
        filing_deadline = extended_deadline(report.tax_year)
    else:
        filing_deadline = None
    updated = service.repo.update(
        report_id, report=report,
        deadline_type=dt, filing_deadline=filing_deadline,
        custom_deadline_note=custom_deadline_note,
    )
    service.repo.append_status_history(
        annual_report_id=report_id,
        from_status=updated.status, to_status=updated.status,
        changed_by=changed_by,
        note=_deadline_note(dt, filing_deadline, custom_deadline_note),
    )
    return updated


def _deadline_note(deadline_type, filing_deadline, custom_deadline_note):
    note = DEADLINE_UPDATED_NOTE.format(
        deadline_type=deadline_type.value,
        filing_deadline=filing_deadline.strftime("%d/%m/%Y") if filing_deadline else CUSTOM_DEADLINE_LABEL,
    )
    return note + (f" — {custom_deadline_note}" if custom_deadline_note else "")
