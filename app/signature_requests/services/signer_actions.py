from __future__ import annotations

from typing import Optional

from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.signature_request_validations import assert_signable, get_by_token_or_raise
from app.utils.time_utils import utcnow


def record_view(
    repo: SignatureRequestRepository,
    *,
    token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignatureRequest:
    req = get_by_token_or_raise(repo, token)
    assert_signable(repo, req)

    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="viewed",
        actor_type="signer",
        actor_name=req.signer_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return req


def sign_request(
    repo: SignatureRequestRepository,
    *,
    token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignatureRequest:
    req = get_by_token_or_raise(repo, token)
    assert_signable(repo, req)

    now = utcnow()
    req = repo.update(
        req.id,
        status=SignatureRequestStatus.SIGNED,
        signed_at=now,
        signer_ip_address=ip_address,
        signer_user_agent=user_agent,
        signing_token=None,
    )

    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="signed",
        actor_type="signer",
        actor_name=req.signer_name,
        ip_address=ip_address,
        user_agent=user_agent,
        notes="Document approved and signed by signer.",
    )

    if req.annual_report_id:
        repo.append_audit_event(
            signature_request_id=req.id,
            event_type="annual_report_signed",
            actor_type="system",
            notes=f"Annual report ID {req.annual_report_id} client approval recorded.",
        )
        _auto_advance_annual_report(repo.db, req.annual_report_id, now)

    return req


SYSTEM_USER_ID = 0
SYSTEM_USER_NAME = "מערכת"


def _auto_advance_annual_report(db, annual_report_id: int, now) -> None:
    try:
        from app.annual_reports.models.annual_report_enums import AnnualReportStatus
        from app.annual_reports.repositories import AnnualReportDetailRepository
        from app.annual_reports.services.annual_report_service import AnnualReportService

        svc = AnnualReportService(db)
        report = svc.repo.get_by_id(annual_report_id)
        if report is None or report.status != AnnualReportStatus.PENDING_CLIENT:
            return

        svc.transition_status(
            report_id=annual_report_id,
            new_status=AnnualReportStatus.SUBMITTED.value,
            changed_by=SYSTEM_USER_ID,
            changed_by_name=SYSTEM_USER_NAME,
            note="הדוח הוגש אוטומטית לאחר אישור לקוח",
        )

        detail_repo = AnnualReportDetailRepository(db)
        detail_repo.upsert(annual_report_id, client_approved_at=now)
    except Exception:
        pass


def decline_request(
    repo: SignatureRequestRepository,
    *,
    token: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignatureRequest:
    req = get_by_token_or_raise(repo, token)
    assert_signable(repo, req)

    now = utcnow()
    req = repo.update(
        req.id,
        status=SignatureRequestStatus.DECLINED,
        declined_at=now,
        signer_ip_address=ip_address,
        signer_user_agent=user_agent,
        decline_reason=reason,
        signing_token=None,
    )

    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="declined",
        actor_type="signer",
        actor_name=req.signer_name,
        ip_address=ip_address,
        user_agent=user_agent,
        notes=reason or "Signer declined without giving a reason.",
    )

    return req
