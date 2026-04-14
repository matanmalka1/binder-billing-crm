from datetime import datetime

from app.annual_reports.models.annual_report_enums import ClientTypeForReport
from app.common.enums import SubmissionMethod


def standard_deadline(
    tax_year: int,
    client_type: ClientTypeForReport | None = None,
    submission_method: SubmissionMethod | None = None,
) -> datetime:
    """Statutory standard deadline by filing profile.

    - Individuals / self-employed / exempt dealers:
      manual 29.05, online/representative 30.06
    - Corporations / control holders:
      31.07
    """
    if client_type in {
        ClientTypeForReport.CORPORATION,
        ClientTypeForReport.PUBLIC_INSTITUTION,
        ClientTypeForReport.CONTROL_HOLDER,
    }:
        return datetime(tax_year + 1, 7, 31, 23, 59, 59)
    if submission_method in {SubmissionMethod.ONLINE, SubmissionMethod.REPRESENTATIVE}:
        return datetime(tax_year + 1, 6, 30, 23, 59, 59)
    return datetime(tax_year + 1, 5, 29, 23, 59, 59)


def extended_deadline(tax_year: int) -> datetime:
    """January 31 two years after the tax year (for authorised reps)."""
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)


__all__ = ["standard_deadline", "extended_deadline"]
