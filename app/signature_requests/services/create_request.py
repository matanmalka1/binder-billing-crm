from __future__ import annotations

import hashlib
from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestType,
)
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository


def create_request(
    repo: SignatureRequestRepository,
    business_repo: BusinessRepository,
    *,
    client_id: int,
    business_id: Optional[int] = None,
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
    """Create a new signature request in DRAFT status.

    client_id is always required — it is the primary anchor.
    business_id is optional; when provided it must belong to the given client_id.
    """
    # Validate business ownership when business_id is supplied
    if business_id is not None:
        business = business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        if business.client_id != client_id:
            raise AppError(
                f"עסק {business_id} אינו שייך ללקוח {client_id}",
                "BUSINESS.CLIENT_MISMATCH",
            )
        # Fall back to business contact details when caller omits them
        if not signer_email and business.contact_email:
            signer_email = business.contact_email
        if not signer_phone and business.contact_phone:
            signer_phone = business.contact_phone

    valid_types = {e.value for e in SignatureRequestType}
    if request_type not in valid_types:
        raise AppError(
            f"סוג בקשה '{request_type}' אינו חוקי. ערכים חוקיים: {sorted(valid_types)}",
            "SIGNATURE_REQUEST.INVALID_TYPE",
        )
    req_type = SignatureRequestType(request_type)

    content_hash = None
    if content_to_hash:
        content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

    req = repo.create(
        client_id=client_id,
        business_id=business_id,
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
        notes=f"בקשת חתימה נוצרה: {title}",
    )

    return req