from __future__ import annotations

from typing import Optional

from app.core.exceptions import AppError
from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.signature_request_validations import get_or_raise_for_update
from app.utils.time_utils import utcnow


def cancel_request(
    repo: SignatureRequestRepository,
    *,
    request_id: int,
    canceled_by: int,
    canceled_by_name: str,
    reason: Optional[str] = None,
) -> SignatureRequest:
    req = get_or_raise_for_update(repo, request_id)

    cancelable = {SignatureRequestStatus.DRAFT, SignatureRequestStatus.PENDING_SIGNATURE}
    if req.status not in cancelable:
        raise AppError(
            f"לא ניתן לבטל בקשה במצב '{req.status.value}'",
            "SIGNATURE_REQUEST.INVALID_STATUS",
        )

    req = repo.update(
        request_id,
        req=req,
        status=SignatureRequestStatus.CANCELED,
        canceled_at=utcnow(),
        canceled_by=canceled_by,
        signing_token=None,
    )

    repo.append_audit_event(
        signature_request_id=request_id,
        event_type="canceled",
        actor_type="advisor",
        actor_id=canceled_by,
        actor_name=canceled_by_name,
        notes=reason or "בוטל על ידי יועץ.",
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
            notes=f"פג תוקף בקשת החתימה ({req.expires_at.date().isoformat()}).",
        )
        count += 1
    return count
