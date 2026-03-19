from typing import Optional
from datetime import datetime

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.annual_reports.models import AnnualReport, AnnualReportStatus, DeadlineType
from app.annual_reports.schemas.annual_report_responses import AnnualReportResponse
from app.utils.time_utils import utcnow
from .constants import VALID_TRANSITIONS
from .deadlines import extended_deadline, standard_deadline
from .base import AnnualReportBaseService


class AnnualReportStatusService(AnnualReportBaseService):

    def _assert_filing_readiness(self, report_id: int) -> None:
        """Raise AppError listing all blocking issues before SUBMITTED transition."""
        from app.annual_reports.services.financial_service import AnnualReportFinancialService
        svc = AnnualReportFinancialService(self.db)
        result = svc.get_readiness_check(report_id)
        if not result.is_ready:
            issues_str = "; ".join(result.issues)
            raise AppError(f"הדוח אינו מוכן להגשה: {issues_str}", "ANNUAL_REPORT.INVALID_STATUS")

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
        valid_statuses = {e.value for e in AnnualReportStatus}
        if new_status not in valid_statuses:
            raise AppError(f"סטטוס לא חוקי '{new_status}'. חוקיים: {sorted(valid_statuses)}", "ANNUAL_REPORT.INVALID_STATUS")
        ns = AnnualReportStatus(new_status)

        if ns not in VALID_TRANSITIONS.get(report.status, set()):
            allowed = [s.value for s in VALID_TRANSITIONS.get(report.status, set())]
            raise AppError(
                f"לא ניתן לעבור מ-'{report.status.value}' ל-'{ns.value}'. "
                f"סטטוסים הבאים מותרים: {allowed}",
                "ANNUAL_REPORT.INVALID_STATUS",
            )

        if ns == AnnualReportStatus.SUBMITTED:
            self._assert_filing_readiness(report_id)

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

        # Cancel stale PENDING_SIGNATURE requests when leaving PENDING_CLIENT (item 15)
        if old_status == AnnualReportStatus.PENDING_CLIENT and ns != AnnualReportStatus.PENDING_CLIENT:
            self._cancel_pending_signature_requests(report_id, changed_by, changed_by_name, "מעבר סטטוס — ביטול בקשת חתימה")

        if ns == AnnualReportStatus.PENDING_CLIENT:
            # Cancel any existing requests before creating a new one (item 13)
            self._cancel_pending_signature_requests(report_id, changed_by, changed_by_name, "כניסה חוזרת ל-PENDING_CLIENT")
            self._trigger_signature_request(updated, changed_by, changed_by_name)

        return self._to_responses([updated])[0]

    def _cancel_pending_signature_requests(
        self, report_id: int, actor_id: int, actor_name: str, reason: str
    ) -> None:
        from app.signature_requests.services.signature_request_service import SignatureRequestService
        from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
        sig_repo = SignatureRequestRepository(self.db)  # type: ignore[attr-defined]
        pending = sig_repo.list_pending_by_annual_report(report_id)
        if not pending:
            return
        svc = SignatureRequestService(self.db)
        for req in pending:
            svc.cancel_request(request_id=req.id, canceled_by=actor_id, canceled_by_name=actor_name, reason=reason)

    def _trigger_signature_request(self, report, created_by: int, created_by_name: str) -> None:
        from app.signature_requests.services.signature_request_service import SignatureRequestService
        business = self.business_repo.get_by_id(report.business_id)
        svc = SignatureRequestService(self.db)
        svc.create_request(
            business_id=report.business_id,
            created_by=created_by,
            created_by_name=created_by_name,
            request_type="ANNUAL_REPORT_APPROVAL",
            title=f"אישור דוח שנתי {report.tax_year}",
            signer_name=business.full_name if business else str(report.business_id),
            annual_report_id=report.id,
        )

    def update_deadline(
        self,
        report_id: int,
        deadline_type: str,
        changed_by: int,
        changed_by_name: str,
        custom_deadline_note: Optional[str] = None,
    ) -> AnnualReportResponse:
        report = self._get_or_raise(report_id)
        valid_deadline_types = {e.value for e in DeadlineType}
        if deadline_type not in valid_deadline_types:
            raise AppError(f"סוג מועד אחרון לא חוקי '{deadline_type}'", "ANNUAL_REPORT.INVALID_TYPE")
        dt = DeadlineType(deadline_type)

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
