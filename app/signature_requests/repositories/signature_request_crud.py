from typing import Optional

from sqlalchemy import func, select
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
        business_id: Optional[int] = None,  # OPTIONAL context
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
        stmt = select(SignatureRequest).where(
            SignatureRequest.id == request_id,
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def get_by_token(self, token: str) -> Optional[SignatureRequest]:
        stmt = select(SignatureRequest).where(
            SignatureRequest.signing_token == token,
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def get_by_id_for_update(self, request_id: int) -> Optional[SignatureRequest]:
        """Fetch with a row-level lock for status transitions."""
        stmt = (
            select(SignatureRequest)
            .where(
                SignatureRequest.id == request_id,
                SignatureRequest.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    def get_by_token_for_update(self, token: str) -> Optional[SignatureRequest]:
        """Fetch by signing token with a row-level lock for signer actions."""
        stmt = (
            select(SignatureRequest)
            .where(
                SignatureRequest.signing_token == token,
                SignatureRequest.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    # ── List by client (primary) ──────────────────────────────────────────────

    def list_by_client_record(
        self,
        client_record_id: int,
        status: Optional[SignatureRequestStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequest]:
        """All requests for a legal entity, regardless of business."""
        stmt = select(SignatureRequest).where(
            SignatureRequest.client_record_id == client_record_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(SignatureRequest.status == status)
        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(SignatureRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return self.db.scalars(stmt).all()

    def count_by_client_record(
        self,
        client_record_id: int,
        status: Optional[SignatureRequestStatus] = None,
    ) -> int:
        stmt = select(func.count(SignatureRequest.id)).where(
            SignatureRequest.client_record_id == client_record_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(SignatureRequest.status == status)
        return self.db.scalar(stmt)

    # ── List by business (scoped view) ────────────────────────────────────────

    def list_by_business(
        self,
        business_id: int,
        status: Optional[SignatureRequestStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[SignatureRequest]:
        stmt = select(SignatureRequest).where(
            SignatureRequest.business_id == business_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(SignatureRequest.status == status)
        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(SignatureRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return self.db.scalars(stmt).all()

    def count_by_business(
        self,
        business_id: int,
        status: Optional[SignatureRequestStatus] = None,
    ) -> int:
        stmt = select(func.count(SignatureRequest.id)).where(
            SignatureRequest.business_id == business_id,
            SignatureRequest.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(SignatureRequest.status == status)
        return self.db.scalar(stmt)

    # ── Pending (global advisor view) ─────────────────────────────────────────

    def list_active(
        self, page: int = 1, page_size: int = 20
    ) -> list[SignatureRequest]:
        offset = (page - 1) * page_size
        stmt = (
            select(SignatureRequest)
            .where(
                SignatureRequest.status.in_(
                    [
                        SignatureRequestStatus.DRAFT,
                        SignatureRequestStatus.PENDING_SIGNATURE,
                    ]
                ),
                SignatureRequest.deleted_at.is_(None),
            )
            .order_by(SignatureRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return self.db.scalars(stmt).all()

    def count_active(self) -> int:
        stmt = select(func.count(SignatureRequest.id)).where(
            SignatureRequest.status.in_(
                [
                    SignatureRequestStatus.DRAFT,
                    SignatureRequestStatus.PENDING_SIGNATURE,
                ]
            ),
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalar(stmt) or 0

    def list_pending(
        self, page: int = 1, page_size: int = 20
    ) -> list[SignatureRequest]:
        offset = (page - 1) * page_size
        stmt = (
            select(SignatureRequest)
            .where(
                SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
                SignatureRequest.deleted_at.is_(None),
            )
            .order_by(SignatureRequest.sent_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        return self.db.scalars(stmt).all()

    def count_pending(self) -> int:
        stmt = select(func.count(SignatureRequest.id)).where(
            SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

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

    def list_pending_by_annual_report(
        self, annual_report_id: int
    ) -> list[SignatureRequest]:
        """Return all PENDING_SIGNATURE requests linked to the given annual report."""
        stmt = select(SignatureRequest).where(
            SignatureRequest.annual_report_id == annual_report_id,
            SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).all()

    def list_expired_pending(self) -> list[SignatureRequest]:
        """Find PENDING_SIGNATURE requests whose expires_at has passed."""
        now = utcnow()
        stmt = select(SignatureRequest).where(
            SignatureRequest.status == SignatureRequestStatus.PENDING_SIGNATURE,
            SignatureRequest.expires_at < now,
            SignatureRequest.expires_at.isnot(None),
            SignatureRequest.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).all()
