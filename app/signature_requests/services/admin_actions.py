from __future__ import annotations

from typing import Optional

from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.helpers import get_or_raise
from app.utils.time import utcnow


def cancel_request(
    repo: SignatureRequestRepository,
    *,
    request_id: int,
    canceled_by: int,
    canceled_by_name: str,
    reason: Optional[str] = None,
) -> SignatureRequest:
    req = get_or_raise(repo, request_id)

    cancelable = {SignatureRequestStatus.DRAFT, SignatureRequestStatus.PENDING_SIGNATURE}
    if req.status not in cancelable:
        raise ValueError(f"Cannot cancel a request in '{req.status.value}' status.")

    req = repo.update(
        request_id,
        status=SignatureRequestStatus.CANCELED,
        canceled_at=utcnow(),
        signing_token=None,
    )

    repo.append_audit_event(
        signature_request_id=request_id,
        event_type="canceled",
        actor_type="advisor",
        actor_id=canceled_by,
        actor_name=canceled_by_name,
        notes=reason or "Canceled by advisor.",
    )

    return req


def expire_overdue_requests(repo: SignatureRequestRepository) -> int:
    """Mark expired pending requests and return count."""
    expired_reqs = repo.list_expired_pending()
    count = 0
    for req in expired_reqs:
        repo.update(
            req.id,
            status=SignatureRequestStatus.EXPIRED,
            signing_token=None,
        )
        repo.append_audit_event(
            signature_request_id=req.id,
            event_type="expired",
            actor_type="system",
            notes=f"Signing deadline passed ({req.expires_at.date().isoformat()}).",
        )
        count += 1
    return count
