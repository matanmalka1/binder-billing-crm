from typing import Optional

from sqlalchemy.orm import Session

from app.signature_requests.models.signature_request import (
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.utils.time_utils import utcnow


class SignatureRequestCrudMixin:
    db: Session

    def create(
        self,
        client_record_id: int,
        created_by: int,
        request_type: SignatureRequestType,
        title: str,
        signer_name: str,
        business_id: Optional[int] = None,       # OPTIONAL context
        description: Optional[str] = None,
        signer_email: Optional[str] = None,
        signer_phone: Optional[str] = None,
        annual_report_id: Optional[int] = None,
        document_id: Optional[int] = None,
        storage_key: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> SignatureRequest:
        req = SignatureRequest(
            client_record_id=client_record_id,
            business_id=business_id,
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
        self.db.flush()
        return req

    def get_by_id(self, request_id: int) -> Optional[SignatureRequest]:
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.id == request_id, SignatureRequest.deleted_at.is_(None))
            .first()
        )

    def get_by_token(self, token: str) -> Optional[SignatureRequest]:
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.signing_token == token, SignatureRequest.deleted_at.is_(None))
            .first()
        )

    def get_by_id_for_update(self, request_id: int) -> Optional[SignatureRequest]:
        """Fetch with a row-level lock for status transitions."""
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.id == request_id, SignatureRequest.deleted_at.is_(None))
            .with_for_update()
            .first()
        )

    def get_by_token_for_update(self, token: str) -> Optional[SignatureRequest]:
        """Fetch by signing token with a row-level lock for signer actions."""
        return (
            self.db.query(SignatureRequest)
            .filter(SignatureRequest.signing_token == token, SignatureRequest.deleted_at.is_(None))
            .with_for_update()
            .first()
        )

    # ── List by client (primary) ──────────────────────────────────────────────

    def list_by_client_record(
        self,
        client_record_id: int,
        status: Optional[SignatureRequestStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequest]:
        """All requests for a legal entity, regardless of business."""
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.client_record_id == client_record_id,
            SignatureRequest.deleted_at.is_(None),
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

    def count_by_client_record(
        self,
        client_record_id: int,
        status: Optional[SignatureRequestStatus] = None,
    ) -> int:
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.client_record_id == client_record_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            query = query.filter(SignatureRequest.status == status)
        return query.count()

    # ── List by business (scoped view) ────────────────────────────────────────

    def list_by_business(
        self,
        business_id: int,
        status: Optional[SignatureRequestStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequest]:
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.business_id == business_id,
            SignatureRequest.deleted_at.is_(None),
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

    def count_by_business(
        self,
        business_id: int,
        status: Optional[SignatureRequestStatus] = None,
    ) -> int:
        query = self.db.query(SignatureRequest).filter(
            SignatureRequest.business_id == business_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            query = query.filter(SignatureRequest.status == status)
        return query.count()

    # ── Pending (global advisor view) ─────────────────────────────────────────

    def list_pending(self, page: int = 1, page_size: int = 20) -> list[SignatureRequest]:
        offset = (page - 1) * page_size
        return (
            self.db.query(SignatureRequest)
            .filter(
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.deleted_at.is_(None),
            )
            .order_by(SignatureRequest.sent_at.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count_pending(self) -> int:
        return (
            self.db.query(SignatureRequest)
            .filter(
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.deleted_at.is_(None),
            )
            .count()
        )

    def update(
        self,
        request_id: int,
        req: Optional[SignatureRequest] = None,
        **fields,
    ) -> Optional[SignatureRequest]:
        """Update fields on a signature request.

        Pass a pre-fetched (optionally locked) ``req`` entity to avoid a second
        SELECT and keep the lock from get_by_id_for_update() / get_by_token_for_update() alive.
        """
        entity = req or self.get_by_id(request_id)
        if entity is None:
            return None
        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.db.flush()
        return entity

    def list_pending_by_annual_report(self, annual_report_id: int) -> list[SignatureRequest]:
        """Return all PENDING_SIGNATURE requests linked to the given annual report."""
        return (
            self.db.query(SignatureRequest)
            .filter(
                SignatureRequest.annual_report_id == annual_report_id,
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.deleted_at.is_(None),
            )
            .all()
        )

    def list_expired_pending(self) -> list[SignatureRequest]:
        """Find PENDING_SIGNATURE requests whose expires_at has passed."""
        now = utcnow()
        return (
            self.db.query(SignatureRequest)
            .filter(
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.expires_at < now,
                SignatureRequest.expires_at.isnot(None),
                SignatureRequest.deleted_at.is_(None),
            )
            .all()
        )
