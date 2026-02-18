from __future__ import annotations

import secrets
from datetime import timedelta

from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.utils.time import utcnow
from app.signature_requests.services.helpers import get_or_raise


DEFAULT_EXPIRY_DAYS = 14


def send_request(
    repo: SignatureRequestRepository,
    *,
    request_id: int,
    sent_by: int,
    sent_by_name: str,
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
) -> SignatureRequest:
    """Transition a DRAFT request to PENDING_SIGNATURE and generate token."""
    req = get_or_raise(repo, request_id)

    if req.status != SignatureRequestStatus.DRAFT:
        raise ValueError(
            f"Cannot send a request in '{req.status.value}' status. Only DRAFT requests can be sent."
        )

    signing_token = secrets.token_urlsafe(32)
    now = utcnow()
    expires_at = now + timedelta(days=expiry_days)

    req = repo.update(
        request_id,
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token=signing_token,
        sent_at=now,
        expires_at=expires_at,
    )

    repo.append_audit_event(
        signature_request_id=request_id,
        event_type="sent",
        actor_type="advisor",
        actor_id=sent_by,
        actor_name=sent_by_name,
        notes=f"Signing request sent. Expires: {expires_at.date().isoformat()}",
    )

    return req
