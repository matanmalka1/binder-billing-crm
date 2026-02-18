"""
Repository for SignatureRequest and SignatureAuditEvent entities.

All writes go through this layer — no direct ORM manipulation in services.
The audit table is append-only: no update or delete methods are provided.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.signature_requests.models.signature_request import (
    SignatureAuditEvent,
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.utils.time import utcnow


class SignatureRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # SignatureRequest CRUD                                                #
    # ------------------------------------------------------------------ #

    def create(
        self,
        client_id: int,
        created_by: int,
        request_type: SignatureRequestType,
        title: str,
        signer_name: str,
        description: Optional[str] = None,
        signer_email: Optional[str] = None,
        signer_phone: Optional[str] = None,
        annual_report_id: Optional[int] = None,
        document_id: Optional[int] = None,
        storage_key: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> SignatureRequest:
        req = SignatureRequest(
            client_id=client_id,
            created_by=created_by,
            request_type=request_type,
            title=title,
            description=description,
            signer_name=signer_name,
            signer_email=signer_email,
            signer_phone=signer_phone,
            annual_report_id=annual_report_id,
            document_id=document_id,
            storage_key=storage_key,
            content_hash=content_hash,
            status=SignatureRequestStatus.DRAFT,
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return req

    def get_by_id(self, request_id: int) -> Optional[SignatureRequest]:
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.id == request_id)
            .first()
        )

    def get_by_token(self, token: str) -> Optional[SignatureRequest]:
        """Look up a request by its public signing token (used in signing URLs)."""
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.signing_token == token)
            .first()
        )

    def list_by_client(
        self,
        client_id: int,
        status: Optional[SignatureRequestStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequest]:
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.client_id == client_id
        )
        if status:
            query = query.filter(SignatureRequest.status == status)
        offset = (page - 1) * page_size
        return (
            query.order_by(SignatureRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_by_client(
        self,
        client_id: int,
        status: Optional[SignatureRequestStatus] = None,
    ) -> int:
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.client_id == client_id
        )
        if status:
            query = query.filter(SignatureRequest.status == status)
        return query.count()

    def list_pending(self, page: int = 1, page_size: int = 20) -> list[SignatureRequest]:
        """All requests currently awaiting a signer response."""
        offset = (page - 1) * page_size
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE)
            .order_by(SignatureRequest.sent_at.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_pending(self) -> int:
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE)
            .count()
        )

    def update(self, request_id: int, **fields) -> Optional[SignatureRequest]:
        req = self.get_by_id(request_id)
        if req is None:
            return None
        for key, value in fields.items():
            if hasattr(req, key):
                setattr(req, key, value)
        self.db.commit()
        self.db.refresh(req)
        return req

    # ------------------------------------------------------------------ #
    # Expiry management                                                    #
    # ------------------------------------------------------------------ #

    def list_expired_pending(self) -> list[SignatureRequest]:
        """Find PENDING_SIGNATURE requests whose expires_at has passed."""
        now = utcnow()
        return (
            self.db.query(SignatureRequest)
            .filter(
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.expires_at < now,
                SignatureRequest.expires_at.isnot(None),
            )
            .all()
        )

    # ------------------------------------------------------------------ #
    # Audit trail (append-only)                                           #
    # ------------------------------------------------------------------ #

    def append_audit_event(
        self,
        signature_request_id: int,
        event_type: str,
        actor_type: str,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SignatureAuditEvent:
        event = SignatureAuditEvent(
            signature_request_id=signature_request_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_name=actor_name,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
            occurred_at=utcnow(),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_audit_events(self, signature_request_id: int) -> list[SignatureAuditEvent]:
        return (
            self.db.query(SignatureAuditEvent)
            .filter(SignatureAuditEvent.signature_request_id == signature_request_id)
            .order_by(SignatureAuditEvent.occurred_at.asc())
            .all()
        )
