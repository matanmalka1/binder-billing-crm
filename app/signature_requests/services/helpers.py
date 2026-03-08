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
        raise ValueError(f"בקשת חתימה {request_id} לא נמצאה")
    return req


def get_by_token_or_raise(repo: SignatureRequestRepository, token: str) -> SignatureRequest:
    req = repo.get_by_token(token)
    if not req:
        raise ValueError("שובר חתימה לא חוקי או כבר בשימוש")
    return req


def assert_signable(repo: SignatureRequestRepository, req: SignatureRequest) -> None:
    """Raise if request is not in a state that allows signer actions."""
    if req.status != SignatureRequestStatus.PENDING_SIGNATURE:
        raise ValueError(
            f"בקשה זו נמצאת בסטטוס '{req.status.value}' ולא ניתן לאשר או לדחות אותה."
        )
    if req.expires_at and utcnow() > req.expires_at:
        repo.update(req.id, status=SignatureRequestStatus.EXPIRED, signing_token=None)
        repo.append_audit_event(
            signature_request_id=req.id,
            event_type="expired",
            actor_type="system",
            notes="Expired detected at signing time.",
        )
        raise ValueError("בקשת החתימה הזו פג תוקף")
