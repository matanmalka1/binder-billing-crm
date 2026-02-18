from __future__ import annotations

from typing import Optional, Tuple, List

from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services.helpers import get_or_raise


def get_request(repo: SignatureRequestRepository, request_id: int) -> Optional[SignatureRequest]:
    return repo.get_by_id(request_id)


def get_by_token(repo: SignatureRequestRepository, token: str) -> Optional[SignatureRequest]:
    return repo.get_by_token(token)


def list_client_requests(
    repo: SignatureRequestRepository,
    *,
    client_id: int,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignatureRequest], int]:
    status_enum = None
    if status:
        try:
            status_enum = SignatureRequestStatus(status)
        except ValueError:
            valid = [e.value for e in SignatureRequestStatus]
            raise ValueError(f"Invalid status '{status}'. Valid: {valid}")

    items = repo.list_by_client(client_id, status=status_enum, page=page, page_size=page_size)
    total = repo.count_by_client(client_id, status=status_enum)
    return items, total


def list_pending_requests(
    repo: SignatureRequestRepository, *, page: int = 1, page_size: int = 20
) -> Tuple[List[SignatureRequest], int]:
    items = repo.list_pending(page=page, page_size=page_size)
    total = repo.count_pending()
    return items, total


def get_audit_trail(repo: SignatureRequestRepository, request_id: int) -> list:
    get_or_raise(repo, request_id)
    return repo.list_audit_events(request_id)
