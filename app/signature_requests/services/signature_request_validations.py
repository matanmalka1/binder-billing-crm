from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError
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


def assert_pending(req: SignatureRequest) -> None:
    """Pure guard — raises if the request cannot receive signer actions.

    Does NOT write to the DB. Callers that detect expiry at signing time must
    handle the EXPIRED transition themselves (see signer_actions.py).
    """
    if req.status != SignatureRequestStatus.PENDING_SIGNATURE:
        raise AppError(
            f"בקשה זו נמצאת בסטטוס '{req.status.value}' ולא ניתן לאשר או לדחות אותה.",
            "SIGNATURE_REQUEST.INVALID_STATUS",
        )


def check_not_expired(req: SignatureRequest) -> bool:
    """Return True if the request is expired (expires_at has passed).

    Does NOT raise — callers decide how to handle it.
    """
    return bool(req.expires_at and utcnow() > req.expires_at)