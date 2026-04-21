"""Signature request helpers for annual report status transitions."""

from app.annual_reports.services.messages import ANNUAL_REPORT_APPROVAL_TITLE


class AnnualReportSignatureHelper:
    """Mixin: manage signature requests during status transitions."""

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
        from app.clients.repositories.client_record_repository import ClientRecordRepository
        record = ClientRecordRepository(self.db).get_by_id(report.client_record_id)  # type: ignore[attr-defined]
        if not record:
            return
        businesses = self.business_repo.list_by_legal_entity(record.legal_entity_id)  # type: ignore[attr-defined]
        business = businesses[0] if businesses else None
        if not business:
            return
        svc = SignatureRequestService(self.db)
        svc.create_request(
            business_id=business.id,
            created_by=created_by,
            created_by_name=created_by_name,
            request_type="ANNUAL_REPORT_APPROVAL",
            title=ANNUAL_REPORT_APPROVAL_TITLE.format(tax_year=report.tax_year),
            signer_name=business.business_name,
            annual_report_id=report.id,
        )
