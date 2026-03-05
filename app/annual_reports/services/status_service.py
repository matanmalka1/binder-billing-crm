from typing import Optional
from datetime import datetime

from app.annual_reports.models import AnnualReport, AnnualReportStatus, DeadlineType
from app.annual_reports.schemas.annual_report import AnnualReportResponse
from app.utils.time import utcnow
from .constants import VALID_TRANSITIONS
from .deadlines import extended_deadline, standard_deadline
from .base import AnnualReportBaseService


class AnnualReportStatusService(AnnualReportBaseService):
    def transition_status(
        self,
        report_id: int,
        new_status: str,
        changed_by: int,
        changed_by_name: str,
        note: Optional[str] = None,
        ita_reference: Optional[str] = None,
        assessment_amount: Optional[float] = None,
        refund_due: Optional[float] = None,
        tax_due: Optional[float] = None,
        submitted_at: Optional[datetime] = None,
    ) -> AnnualReportResponse:
        report = self._get_or_raise(report_id)
        try:
            ns = AnnualReportStatus(new_status)
        except ValueError:
            valid = [e.value for e in AnnualReportStatus]
            raise ValueError(f"סטטוס לא חוקי '{new_status}'. חוקיים: {valid}")

        if ns not in VALID_TRANSITIONS.get(report.status, set()):
            allowed = [s.value for s in VALID_TRANSITIONS.get(report.status, set())]
            raise ValueError(
                f"לא ניתן לעבור מ-'{report.status.value}' ל-'{ns.value}'. "
                f"סטטוסים הבאים מותרים: {allowed}"
                    )

        update_fields: dict = {"status": ns}

        if ns == AnnualReportStatus.SUBMITTED:
            update_fields["submitted_at"] = submitted_at or utcnow()
            if ita_reference:
                update_fields["ita_reference"] = ita_reference

        if ns == AnnualReportStatus.ASSESSMENT_ISSUED:
            if assessment_amount is not None:
                update_fields["assessment_amount"] = assessment_amount
            if refund_due is not None:
                update_fields["refund_due"] = refund_due
            if tax_due is not None:
                update_fields["tax_due"] = tax_due

        old_status = report.status
        updated = self.repo.update(report_id, **update_fields)

        self.repo.append_status_history(
            annual_report_id=report_id,
            from_status=old_status,
            to_status=ns,
            changed_by=changed_by,
            changed_by_name=changed_by_name,
            note=note,
        )

        return self._to_responses([updated])[0]

    def update_deadline(
        self,
        report_id: int,
        deadline_type: str,
        changed_by: int,
        changed_by_name: str,
        custom_deadline_note: Optional[str] = None,
    ) -> AnnualReportResponse:
        report = self._get_or_raise(report_id)
        try:
            dt = DeadlineType(deadline_type)
        except ValueError:
            raise ValueError(f"סוג מועד אחרון לא חוקי '{deadline_type}'")

        if dt == DeadlineType.STANDARD:
            filing_deadline = standard_deadline(report.tax_year)
        elif dt == DeadlineType.EXTENDED:
            filing_deadline = extended_deadline(report.tax_year)
        else:
            filing_deadline = None

        updated = self.repo.update(
            report_id,
            deadline_type=dt,
            filing_deadline=filing_deadline,
            custom_deadline_note=custom_deadline_note,
        )

        self.repo.append_status_history(
            annual_report_id=report_id,
            from_status=updated.status,
            to_status=updated.status,
            changed_by=changed_by,
            changed_by_name=changed_by_name,
            note=(
                f"המועד האחרון עודכן ל-{dt.value}: "
                f"{filing_deadline.strftime('%d/%m/%Y') if filing_deadline else 'מותאם אישית'}"
                + (f" — {custom_deadline_note}" if custom_deadline_note else "")
            ),
        )

        return self._to_responses([updated])[0]
