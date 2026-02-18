from __future__ import annotations

from typing import Optional

from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.utils.time import utcnow


def get_or_raise(repo: SignatureRequestRepository, request_id: int) -> SignatureRequest:
    req = repo.get_by_id(request_id)
    if not req:
        raise ValueError(f"Signature request {request_id} not found")
    return req


def get_by_token_or_raise(repo: SignatureRequestRepository, token: str) -> SignatureRequest:
    req = repo.get_by_token(token)
    if not req:
        raise ValueError("Invalid or already-used signing token")
    return req


def assert_signable(repo: SignatureRequestRepository, req: SignatureRequest) -> None:
    """Raise if request is not in a state that allows signer actions."""
    if req.status != SignatureRequestStatus.PENDING_SIGNATURE:
        raise ValueError(
            f"This request is '{req.status.value}' and cannot be signed or declined."
        )
    if req.expires_at and utcnow() > req.expires_at:
        repo.update(req.id, status=SignatureRequestStatus.EXPIRED, signing_token=None)
        repo.append_audit_event(
            signature_request_id=req.id,
            event_type="expired",
            actor_type="system",
            notes="Expired detected at signing time.",
        )
        raise ValueError("This signing request has expired.")
