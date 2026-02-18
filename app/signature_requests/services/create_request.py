from __future__ import annotations

import hashlib
from typing import Optional

from app.clients.repositories.client_repository import ClientRepository
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestType,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository


def create_request(
    repo: SignatureRequestRepository,
    client_repo: ClientRepository,
    *,
    client_id: int,
    created_by: int,
    created_by_name: str,
    request_type: str,
    title: str,
    signer_name: str,
    description: Optional[str] = None,
    signer_email: Optional[str] = None,
    signer_phone: Optional[str] = None,
    annual_report_id: Optional[int] = None,
    document_id: Optional[int] = None,
    storage_key: Optional[str] = None,
    content_to_hash: Optional[str] = None,
) -> SignatureRequest:
    """Create a new signature request in DRAFT status."""
    client = client_repo.get_by_id(client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    try:
        req_type = SignatureRequestType(request_type)
    except ValueError:
        valid = [e.value for e in SignatureRequestType]
        raise ValueError(f"Invalid request_type '{request_type}'. Valid values: {valid}")

    content_hash = None
    if content_to_hash:
        content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

    if not signer_email and client.email:
        signer_email = client.email
    if not signer_phone and client.phone:
        signer_phone = client.phone

    req = repo.create(
        client_id=client_id,
        created_by=created_by,
        request_type=req_type,
        title=title,
        description=description,
        signer_name=signer_name,
        signer_email=signer_email,
        signer_phone=signer_phone,
        annual_report_id=annual_report_id,
        document_id=document_id,
        storage_key=storage_key,
        content_hash=content_hash,
    )

    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="created",
        actor_type="advisor",
        actor_id=created_by,
        actor_name=created_by_name,
        notes=f"Request created: {title}",
    )

    return req
