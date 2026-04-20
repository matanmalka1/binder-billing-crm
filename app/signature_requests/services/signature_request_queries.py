from __future__ import annotations

from typing import List, Optional, Tuple

from app.core.exceptions import AppError
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.signature_requests.services.messages import INVALID_FILTER_STATUS
from app.signature_requests.services.signature_request_validations import get_or_raise


def get_request(repo: SignatureRequestRepository, request_id: int) -> Optional[SignatureRequest]:
    return repo.get_by_id(request_id)


def get_by_token(repo: SignatureRequestRepository, token: str) -> Optional[SignatureRequest]:
    return repo.get_by_token(token)


def _parse_status(status: Optional[str]) -> Optional[SignatureRequestStatus]:
    if not status:
        return None
    valid_statuses = {e.value for e in SignatureRequestStatus}
    if status not in valid_statuses:
        raise AppError(
            INVALID_FILTER_STATUS.format(status=status, valid_statuses=sorted(valid_statuses)),
            "SIGNATURE_REQUEST.INVALID_STATUS",
        )
    return SignatureRequestStatus(status)


def list_client_requests(
    repo: SignatureRequestRepository,
    *,
    client_record_id: int,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignatureRequest], int]:
    """All signature requests for a legal entity (primary query path)."""
    status_enum = _parse_status(status)
    client_record_id = ClientRecordRepository(repo.db).get_by_client_id(client_record_id).id
    items = repo.list_by_client_record(client_record_id, status=status_enum, page=page, page_size=page_size)
    total = repo.count_by_client_record(client_record_id, status=status_enum)
    return items, total


def list_business_requests(
    repo: SignatureRequestRepository,
    *,
    business_id: int,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignatureRequest], int]:
    """Signature requests scoped to a specific business (secondary / filtered view)."""
    status_enum = _parse_status(status)
    items = repo.list_by_business(business_id, status=status_enum, page=page, page_size=page_size)
    total = repo.count_by_business(business_id, status=status_enum)
    return items, total


def list_pending_requests(
    repo: SignatureRequestRepository,
    *,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignatureRequest], int]:
    items = repo.list_pending(page=page, page_size=page_size)
    total = repo.count_pending()
    return items, total


def get_audit_trail(repo: SignatureRequestRepository, request_id: int) -> list:
    get_or_raise(repo, request_id)
    return repo.list_audit_events(request_id)
