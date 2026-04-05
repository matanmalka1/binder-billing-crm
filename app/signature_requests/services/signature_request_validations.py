from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.signature_requests.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.utils.time_utils import utcnow


def get_or_raise(repo: SignatureRequestRepository, request_id: int) -> SignatureRequest:
    req = repo.get_by_id(request_id)
    if not req:
        raise NotFoundError(f"בקשת חתימה {request_id} לא נמצאה", "SIGNATURE_REQUEST.NOT_FOUND")
    return req


def get_or_raise_for_update(repo: SignatureRequestRepository, request_id: int) -> SignatureRequest:
    """Fetch with a row-level lock. Use for transition entrypoints."""
    req = repo.get_by_id_for_update(request_id)
    if not req:
        raise NotFoundError(f"בקשת חתימה {request_id} לא נמצאה", "SIGNATURE_REQUEST.NOT_FOUND")
    return req


def get_by_token_or_raise(repo: SignatureRequestRepository, token: str) -> SignatureRequest:
    req = repo.get_by_token(token)
    if not req:
        raise AppError("שובר חתימה לא חוקי או כבר בשימוש", "SIGNATURE_REQUEST.TOKEN_INVALID")
    return req


def get_by_token_or_raise_for_update(repo: SignatureRequestRepository, token: str) -> SignatureRequest:
    """Fetch by token with a row-level lock. Use for signer transition entrypoints."""
    req = repo.get_by_token_for_update(token)
    if not req:
        raise AppError("שובר חתימה לא חוקי או כבר בשימוש", "SIGNATURE_REQUEST.TOKEN_INVALID")
    return req


def assert_signable(repo: SignatureRequestRepository, req: SignatureRequest) -> None:
    """Raise if request is not in a state that allows signer actions."""
    if req.status != SignatureRequestStatus.PENDING_SIGNATURE:
        raise AppError(
            f"בקשה זו נמצאת בסטטוס '{req.status.value}' ולא ניתן לאשר או לדחות אותה.",
            "SIGNATURE_REQUEST.INVALID_STATUS",
        )
    if req.expires_at and utcnow() > req.expires_at:
        repo.update(req.id, status=SignatureRequestStatus.EXPIRED, signing_token=None)
        repo.append_audit_event(
            signature_request_id=req.id,
            event_type="expired",
            actor_type="system",
            notes="Expired detected at signing time.",
        )
        raise AppError("בקשת החתימה הזו פג תוקף", "SIGNATURE_REQUEST.EXPIRED")
