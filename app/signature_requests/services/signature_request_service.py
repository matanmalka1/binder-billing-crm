from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import AppError, NotFoundError
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
)
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.signature_requests.services import (
    admin_actions,
    create_request,
    send_request,
    signer_actions,
)
from app.signature_requests.services.messages import (
    AUTO_ADVANCE_ANNUAL_REPORT_ERROR,
    ANNUAL_REPORT_SIGNED_NOTE,
    AUTO_SUBMITTED_AFTER_SIGNATURE_NOTE,
    INVALID_FILTER_STATUS,
    SYSTEM_USER_NAME,
)
from app.signature_requests.services.signature_request_validations import get_or_raise

_log = logging.getLogger(__name__)

_SYSTEM_USER_ID = 0
_SYSTEM_USER_NAME = SYSTEM_USER_NAME


class SignatureRequestService:
    """Orchestrates digital signature request lifecycle."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SignatureRequestRepository(db)
        self.business_repo = BusinessRepository(db)

    # ── Create ────────────────────────────────────────────────────────────────

    def create_request(self, **kwargs):
        return create_request.create_request(self.repo, self.business_repo, **kwargs)

    def create_and_send_request(
        self,
        *,
        sent_by: int,
        sent_by_name: str,
        expiry_days: int,
        **create_kwargs,
    ):
        req = self.create_request(**create_kwargs)
        return self.send_request(
            request_id=req.id,
            sent_by=sent_by,
            sent_by_name=sent_by_name,
            expiry_days=expiry_days,
        )

    # ── Send ──────────────────────────────────────────────────────────────────

    def send_request(self, **kwargs):
        return send_request.send_request(self.repo, **kwargs)

    # ── Signer actions ────────────────────────────────────────────────────────

    def record_view(self, **kwargs):
        return signer_actions.record_view(self.repo, **kwargs)

    def sign_request(self, **kwargs):
        req, annual_report_id, signed_at = signer_actions.sign_request(
            self.repo, **kwargs
        )
        if annual_report_id:
            self.repo.append_audit_event(
                signature_request_id=req.id,
                event_type="annual_report_signed",
                actor_type="system",
                notes=ANNUAL_REPORT_SIGNED_NOTE.format(
                    annual_report_id=annual_report_id
                ),
            )
            self._auto_advance_annual_report(annual_report_id, signed_at)
        return req

    def decline_request(self, **kwargs):
        return signer_actions.decline_request(self.repo, **kwargs)

    def _auto_advance_annual_report(self, annual_report_id: int, now) -> None:
        try:
            from app.annual_reports.models.annual_report_enums import AnnualReportStatus
            from app.annual_reports.repositories.detail_repository import (
                AnnualReportDetailRepository,
            )
            from app.annual_reports.services.annual_report_service import (
                AnnualReportService,
            )

            svc = AnnualReportService(self.db)
            report = svc.repo.get_by_id(annual_report_id)
            if report is None or report.status != AnnualReportStatus.PENDING_CLIENT:
                return
            svc.transition_status(
                report_id=annual_report_id,
                new_status=AnnualReportStatus.SUBMITTED.value,
                changed_by=_SYSTEM_USER_ID,
                changed_by_name=_SYSTEM_USER_NAME,
                note=AUTO_SUBMITTED_AFTER_SIGNATURE_NOTE,
            )
            detail_repo = AnnualReportDetailRepository(self.db)
            detail_repo.update_meta(annual_report_id, client_approved_at=now)
        except Exception:
            _log.exception(AUTO_ADVANCE_ANNUAL_REPORT_ERROR, annual_report_id)

    # ── Advisor / system actions ──────────────────────────────────────────────

    def cancel_request(self, **kwargs):
        return admin_actions.cancel_request(self.repo, **kwargs)

    def expire_overdue_requests(self):
        return admin_actions.expire_overdue_requests(self.repo)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_request(self, request_id: int) -> Optional[SignatureRequest]:
        return self.repo.get_by_id(request_id)

    def get_by_token(self, token: str) -> Optional[SignatureRequest]:
        return self.repo.get_by_token(token)

    def list_client_requests(
        self,
        *,
        client_record_id: int,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SignatureRequest], int]:
        status_enum = self._parse_status(status)
        record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if not record:
            raise NotFoundError(
                f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND"
            )
        items = self.repo.list_by_client_record(
            client_record_id, status=status_enum, page=page, page_size=page_size
        )
        total = self.repo.count_by_client_record(client_record_id, status=status_enum)
        return items, total

    def list_pending_requests(
        self, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[SignatureRequest], int]:
        items = self.repo.list_pending(page=page, page_size=page_size)
        total = self.repo.count_pending()
        return items, total

    def get_audit_trail(self, request_id: int) -> list:
        get_or_raise(self.repo, request_id)
        return self.repo.list_audit_events(request_id)

    @staticmethod
    def _parse_status(status: Optional[str]) -> Optional[SignatureRequestStatus]:
        if not status:
            return None
        valid_statuses = {e.value for e in SignatureRequestStatus}
        if status not in valid_statuses:
            raise AppError(
                INVALID_FILTER_STATUS.format(
                    status=status, valid_statuses=sorted(valid_statuses)
                ),
                "SIGNATURE_REQUEST.INVALID_STATUS",
            )
        return SignatureRequestStatus(status)
