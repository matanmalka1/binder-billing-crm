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
# ─── SignatureRequest ─────────────────────────────────────────────────────────

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow

 
class SignatureRequestStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELED = "canceled"
 
 
class SignatureRequestType(str, PyEnum):
    ENGAGEMENT_AGREEMENT = "engagement_agreement"
    ANNUAL_REPORT_APPROVAL = "annual_report_approval"
    POWER_OF_ATTORNEY = "power_of_attorney"
    VAT_RETURN_APPROVAL = "vat_return_approval"
    CUSTOM = "custom"
 
 
class SignatureRequest(Base):
    __tablename__ = "signature_requests"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("permanent_documents.id"), nullable=True)
 
    request_type = Column(pg_enum(SignatureRequestType), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    storage_key = Column(String, nullable=True)
 
    signer_name = Column(String, nullable=False)
    signer_email = Column(String, nullable=True)
    signer_phone = Column(String, nullable=True)
 
    status = Column(pg_enum(SignatureRequestStatus), default=SignatureRequestStatus.DRAFT, nullable=False)
    signing_token = Column(String, unique=True, nullable=True, index=True)
 
    created_at = Column(DateTime, default=utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
 
    signer_ip_address = Column(String, nullable=True)
    signer_user_agent = Column(String, nullable=True)
    decline_reason = Column(Text, nullable=True)
    signed_document_key = Column(String, nullable=True)
 
    __table_args__ = (
        Index("idx_sig_request_business", "business_id"),
        Index("idx_sig_request_status", "status"),
        Index("idx_sig_request_token", "signing_token"),
        Index("idx_sig_request_annual_report", "annual_report_id"),
    )
 
    def __repr__(self):
        return (
            f"<SignatureRequest(id={self.id}, business_id={self.business_id}, "
            f"type='{self.request_type}', status='{self.status}')>"
        )