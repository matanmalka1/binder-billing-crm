from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.signature_requests.services.messages import (
    BUSINESS_NOT_FOUND,
    INVALID_REQUEST_TYPE,
    SIGNATURE_REQUEST_CREATED_NOTE,
    SIGNATURE_REQUEST_SENT_NOTE,
)
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import (
    assert_business_belongs_to_legal_entity,
)
from app.businesses.services.business_contact_service import BusinessContactService
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.utils.time_utils import utcnow


def create_request(
    repo: SignatureRequestRepository,
    business_repo: BusinessRepository,
    *,
    client_record_id: int,
    business_id: Optional[int] = None,
    created_by: int,
    created_by_name: str,
    sent_by: int,
    sent_by_name: str,
    expiry_days: int,
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
    """Create and send a signature request in PENDING_SIGNATURE status.

    client_record_id is always required — it is the primary anchor.
    business_id is optional; when provided it must belong to the given client_record_id.
    """
    client_record = ClientRecordRepository(repo.db).get_by_id(client_record_id)
    if not client_record:
        raise NotFoundError(
            f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND"
        )

    # Validate business ownership when business_id is supplied
    if business_id is not None:
        business = business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(
                BUSINESS_NOT_FOUND.format(business_id=business_id), "BUSINESS.NOT_FOUND"
            )
        assert_business_belongs_to_legal_entity(business, client_record.legal_entity_id)
        contact_service = BusinessContactService(repo.db)
        contact_email = contact_service.contact_email(business)
        contact_phone = contact_service.contact_phone(business)
        if not signer_email and contact_email:
            signer_email = contact_email
        if not signer_phone and contact_phone:
            signer_phone = contact_phone

    valid_types = {e.value for e in SignatureRequestType}
    if request_type not in valid_types:
        raise AppError(
            INVALID_REQUEST_TYPE.format(
                request_type=request_type,
                valid_types=sorted(valid_types),
            ),
            "SIGNATURE_REQUEST.INVALID_TYPE",
        )
    req_type = SignatureRequestType(request_type)

    content_hash = None
    if content_to_hash:
        content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

    now = utcnow()
    expires_at = now + timedelta(days=expiry_days)

    req = repo.create(
        client_record_id=client_record.id,
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
        status=SignatureRequestStatus.PENDING_SIGNATURE,
        signing_token=secrets.token_urlsafe(32),
        sent_at=now,
        expires_at=expires_at,
        expiry_days=expiry_days,
    )

    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="created",
        actor_type="advisor",
        actor_id=created_by,
        actor_name=created_by_name,
        notes=SIGNATURE_REQUEST_CREATED_NOTE.format(title=title),
    )
    repo.append_audit_event(
        signature_request_id=req.id,
        event_type="sent",
        actor_type="advisor",
        actor_id=sent_by,
        actor_name=sent_by_name,
        notes=SIGNATURE_REQUEST_SENT_NOTE.format(
            expires_at=expires_at.date().isoformat()
        ),
    )

    return req
