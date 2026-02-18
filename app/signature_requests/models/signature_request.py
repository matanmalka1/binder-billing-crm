"""
Digital Signature Request model.

Tracks the full lifecycle of a document signature request:
  DRAFT → PENDING_SIGNATURE → SIGNED | DECLINED | EXPIRED

Each request targets a specific document (or ad-hoc content) and
captures a tamper-evident audit trail of every state transition.

Israeli legal context:
  The Electronic Signature Law (5761-2001) recognises digital signatures
  as legally binding when coupled with an audit trail that proves:
    - Who was asked to sign (identity)
    - When they were asked (timestamp)
    - What they approved (content hash)
    - How they confirmed (action timestamp + IP)
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from app.database import Base
from app.utils.time import utcnow


class SignatureRequestStatus(str, PyEnum):
    DRAFT = "draft"                       # Created, not yet sent
    PENDING_SIGNATURE = "pending_signature"  # Sent to signer, awaiting response
    SIGNED = "signed"                     # Signer approved
    DECLINED = "declined"                 # Signer explicitly declined
    EXPIRED = "expired"                   # Deadline passed without response
    CANCELED = "canceled"                 # Advisor canceled before signing


class SignatureRequestType(str, PyEnum):
    """What kind of document is being signed."""
    ENGAGEMENT_AGREEMENT = "engagement_agreement"   # הסכם ייפוי כוח
    ANNUAL_REPORT_APPROVAL = "annual_report_approval"  # אישור דוח שנתי
    POWER_OF_ATTORNEY = "power_of_attorney"         # ייפוי כוח
    VAT_RETURN_APPROVAL = "vat_return_approval"     # אישור דוח מע"מ
    CUSTOM = "custom"                               # Free-form


class SignatureRequest(Base):
    __tablename__ = "signature_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core relationships
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Optional links to other entities
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("permanent_documents.id"), nullable=True)

    # Request metadata
    request_type = Column(Enum(SignatureRequestType), nullable=False)
    title = Column(String, nullable=False)          # Human-readable subject
    description = Column(Text, nullable=True)       # What is being signed & why
    content_hash = Column(String, nullable=True)    # SHA-256 of document content (tamper evidence)
    storage_key = Column(String, nullable=True)     # Path to the document to be signed

    # Signer information
    signer_name = Column(String, nullable=False)
    signer_email = Column(String, nullable=True)
    signer_phone = Column(String, nullable=True)

    # Lifecycle
    status = Column(
        Enum(SignatureRequestStatus),
        default=SignatureRequestStatus.DRAFT,
        nullable=False,
    )

    # Token used in the public signing URL (UUID, single-use)
    signing_token = Column(String, unique=True, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)    # Hard deadline for signing
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # Audit evidence captured at signing time
    signer_ip_address = Column(String, nullable=True)
    signer_user_agent = Column(String, nullable=True)
    decline_reason = Column(Text, nullable=True)

    # Signed document storage
    signed_document_key = Column(String, nullable=True)  # Archived signed copy

    __table_args__ = (
        Index("idx_sig_request_client", "client_id"),
        Index("idx_sig_request_status", "status"),
        Index("idx_sig_request_token", "signing_token"),
        Index("idx_sig_request_annual_report", "annual_report_id"),
    )

    def __repr__(self):
        return (
            f"<SignatureRequest(id={self.id}, client_id={self.client_id}, "
            f"type='{self.request_type}', status='{self.status}')>"
        )


class SignatureAuditEvent(Base):
    """
    Immutable append-only audit trail for every state change on a SignatureRequest.

    This is the legal record — never update or delete rows in this table.
    Each event records WHO did WHAT, WHEN, and from WHERE (IP).
    """

    __tablename__ = "signature_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signature_request_id = Column(
        Integer, ForeignKey("signature_requests.id"), nullable=False, index=True
    )

    event_type = Column(String, nullable=False)   # e.g. "sent", "viewed", "signed", "declined"
    actor_type = Column(String, nullable=False)   # "advisor" | "signer" | "system"
    actor_id = Column(Integer, nullable=True)     # user.id if advisor, null if signer/system
    actor_name = Column(String, nullable=True)    # Display name for the audit log

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    occurred_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_sig_audit_request", "signature_request_id"),
        Index("idx_sig_audit_occurred", "occurred_at"),
    )

    def __repr__(self):
        return (
            f"<SignatureAuditEvent(id={self.id}, "
            f"request_id={self.signature_request_id}, "
            f"event='{self.event_type}')>"
        )
