from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services import (
    admin_actions,
    create_request,
    send_request,
    signature_request_queries,
    signer_actions,
)

_log = logging.getLogger(__name__)

_SYSTEM_USER_ID = 0
_SYSTEM_USER_NAME = "מערכת"


class SignatureRequestService:
    """
    Orchestrates digital signature request lifecycle.
    Thin façade delegating to smaller feature modules.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = SignatureRequestRepository(db)
        self.business_repo = BusinessRepository(db)

    # Create
    def create_request(self, **kwargs):
        return create_request.create_request(self.repo, self.business_repo, **kwargs)

    # Send
    def send_request(self, **kwargs):
        return send_request.send_request(self.repo, **kwargs)

    # Signer actions
    def record_view(self, **kwargs):
        return signer_actions.record_view(self.repo, **kwargs)

    def sign_request(self, **kwargs):
        req, annual_report_id, signed_at = signer_actions.sign_request(self.repo, **kwargs)
        if annual_report_id:
            self.repo.append_audit_event(
                signature_request_id=req.id,
                event_type="annual_report_signed",
                actor_type="system",
                notes=f"אישור לקוח נרשם לדוח שנתי מספר {annual_report_id}.",
            )
            self._auto_advance_annual_report(annual_report_id, signed_at)
        return req

    def decline_request(self, **kwargs):
        return signer_actions.decline_request(self.repo, **kwargs)

    def _auto_advance_annual_report(self, annual_report_id: int, now) -> None:
        try:
            from app.annual_reports.models.annual_report_enums import AnnualReportStatus
            from app.annual_reports.repositories import AnnualReportDetailRepository
            from app.annual_reports.services.annual_report_service import AnnualReportService

            svc = AnnualReportService(self.db)
            # Cheap early-exit guard — no lock here.
            # transition_status() acquires the row-level lock internally via
            # _get_or_raise_for_update(). The sig_request lock was already released
            # by the commit in sign_request(), so there is no cross-lock deadlock.
            # Lock ordering invariant: annual_report is always locked after sig_request commits.
            report = svc.repo.get_by_id(annual_report_id)
            if report is None or report.status != AnnualReportStatus.PENDING_CLIENT:
                return

            svc.transition_status(
                report_id=annual_report_id,
                new_status=AnnualReportStatus.SUBMITTED.value,
                changed_by=_SYSTEM_USER_ID,
                changed_by_name=_SYSTEM_USER_NAME,
                note="הדוח הוגש אוטומטית לאחר אישור לקוח",
            )

            detail_repo = AnnualReportDetailRepository(self.db)
            detail_repo.upsert(annual_report_id, client_approved_at=now)
        except Exception:
            _log.exception("שגיאה בקידום אוטומטי של דוח שנתי %s לאחר חתימה", annual_report_id)

    # Advisor/system actions
    def cancel_request(self, **kwargs):
        return admin_actions.cancel_request(self.repo, **kwargs)

    def expire_overdue_requests(self):
        return admin_actions.expire_overdue_requests(self.repo)

    # Queries
    def get_request(self, request_id: int):
        return signature_request_queries.get_request(self.repo, request_id)

    def get_by_token(self, token: str):
        return signature_request_queries.get_by_token(self.repo, token)

    def list_business_requests(self, **kwargs):
        return signature_request_queries.list_business_requests(self.repo, **kwargs)

    def list_pending_requests(self, **kwargs):
        return signature_request_queries.list_pending_requests(self.repo, **kwargs)

    def get_audit_trail(self, request_id: int):
        return signature_request_queries.get_audit_trail(self.repo, request_id)
