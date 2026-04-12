from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.signature_request_validations import (
    assert_pending,
    check_not_expired,
    get_by_token_or_raise,
    get_by_token_or_raise_for_update,
)
from app.utils.time_utils import utcnow


def _expire_and_raise(repo: SignatureRequestRepository, req: SignatureRequest) -> None:
    """Transition to EXPIRED and raise. Called only when expiry is detected at signing time."""
    repo.update(req.id, req=req, status=SignatureRequestStatus.EXPIRED, signing_token=None)
    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="expired",
        actor_type="system",
        notes=f"פג תוקף בקשת החתימה ({req.expires_at.date().isoformat()}).",
    )
    from app.core.exceptions import AppError
    raise AppError("בקשת החתימה הזו פג תוקף", "SIGNATURE_REQUEST.EXPIRED")


def record_view(
    repo: SignatureRequestRepository,
    *,
    token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignatureRequest:
    req = get_by_token_or_raise(repo, token)
    assert_pending(req)
    if check_not_expired(req):
        _expire_and_raise(repo, req)

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
) -> tuple[SignatureRequest, Optional[int], Optional[datetime]]:
    """Returns (req, annual_report_id, signed_at) so the façade can handle cross-domain side-effects."""
    req = get_by_token_or_raise_for_update(repo, token)
    assert_pending(req)
    if check_not_expired(req):
        _expire_and_raise(repo, req)

    now = utcnow()
    req = repo.update(
        req.id,
        req=req,
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
        notes="מסמך אושר ונחתם על ידי החותם.",
    )

    return req, req.annual_report_id, now


def decline_request(
    repo: SignatureRequestRepository,
    *,
    token: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SignatureRequest:
    req = get_by_token_or_raise_for_update(repo, token)
    assert_pending(req)
    if check_not_expired(req):
        _expire_and_raise(repo, req)

    now = utcnow()
    req = repo.update(
        req.id,
        req=req,
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
        notes=reason or "החותם דחה את הבקשה ללא הסבר.",
    )

    return req