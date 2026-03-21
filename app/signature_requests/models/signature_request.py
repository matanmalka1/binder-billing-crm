"""
Digital Signature Request — tracks the full lifecycle of a signature request.

  DRAFT → PENDING_SIGNATURE → SIGNED | DECLINED | EXPIRED | CANCELED

Israeli legal context:
  The Electronic Signature Law (5761-2001) recognises digital signatures
  as legally binding when coupled with an audit trail that proves:
    - Who was asked to sign (identity)
    - When they were asked (timestamp)
    - What they approved (content hash)
    - How they confirmed (action timestamp + IP)

Design decisions:
- signing_token is a one-time URL-safe token generated at send time;
  cleared (set NULL) after signing/declining/canceling/expiring.
- content_hash (SHA-256) enables tamper detection of the signed content.
- signed_document_key stores the countersigned PDF in S3/R2.
- canceled_by: who canceled (advisor/system) — separate from deleted_by.
- SignatureAuditEvent is append-only — no soft delete, no updated_at.
- event_type and actor_type are String (not enum) — expand freely without migrations.
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index, Integer, String, Text,
)
from app.utils.enum_utils import pg_enum

from app.database import Base
from app.utils.time_utils import utcnow


class SignatureRequestStatus(str, PyEnum):
    DRAFT             = "draft"
    PENDING_SIGNATURE = "pending_signature"
    SIGNED            = "signed"
    DECLINED          = "declined"
    EXPIRED           = "expired"
    CANCELED          = "canceled"


class SignatureRequestType(str, PyEnum):
    ENGAGEMENT_AGREEMENT  = "engagement_agreement"   # הסכם התקשרות
    ANNUAL_REPORT_APPROVAL = "annual_report_approval" # אישור דוח שנתי
    POWER_OF_ATTORNEY     = "power_of_attorney"       # ייפוי כוח
    VAT_RETURN_APPROVAL   = "vat_return_approval"     # אישור דוח מע"מ
    CUSTOM                = "custom"                  # חתימה כללית


class SignatureRequest(Base):
    __tablename__ = "signature_requests"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    created_by  = Column(Integer, ForeignKey("users.id"),      nullable=False)

    # ── Cross-domain links ────────────────────────────────────────────────────
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"),      nullable=True, index=True)
    document_id      = Column(Integer, ForeignKey("permanent_documents.id"), nullable=True)

    # ── Request identity ──────────────────────────────────────────────────────
    request_type = Column(pg_enum(SignatureRequestType), nullable=False)
    title        = Column(String, nullable=False)
    description  = Column(Text,   nullable=True)
    content_hash = Column(String, nullable=True)   # SHA-256 של התוכן לחתימה
    storage_key  = Column(String, nullable=True)   # מפתח ב-S3/R2 לקובץ המקורי

    # ── Signer identity ───────────────────────────────────────────────────────
    signer_name  = Column(String, nullable=False)
    signer_email = Column(String, nullable=True)
    signer_phone = Column(String, nullable=True)

    # ── Status & token ────────────────────────────────────────────────────────
    status        = Column(pg_enum(SignatureRequestStatus),
                           default=SignatureRequestStatus.DRAFT, nullable=False)
    signing_token = Column(String, unique=True, nullable=True, index=True)
    # token cleared (NULL) after signing/declining/canceling/expiring

    # ── Lifecycle timestamps ──────────────────────────────────────────────────
    created_at  = Column(DateTime, default=utcnow, nullable=False)
    sent_at     = Column(DateTime, nullable=True)
    expires_at  = Column(DateTime, nullable=True)
    signed_at   = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    canceled_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # מי ביטל

    # ── Signer evidence (captured at signing/declining time) ──────────────────
    signer_ip_address   = Column(String, nullable=True)
    signer_user_agent   = Column(String, nullable=True)
    decline_reason      = Column(Text,   nullable=True)
    signed_document_key = Column(String, nullable=True)  # PDF חתום ב-S3/R2

    # ── Soft delete ───────────────────────────────────────────────────────────
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_sig_request_business",      "business_id"),
        Index("idx_sig_request_status",        "status"),
        Index("idx_sig_request_token",         "signing_token"),
        Index("idx_sig_request_annual_report", "annual_report_id"),
    )

    def __repr__(self):
        return (
            f"<SignatureRequest(id={self.id}, business_id={self.business_id}, "
            f"type='{self.request_type}', status='{self.status}')>"
        )


class SignatureAuditEvent(Base):
    """Append-only audit trail — no soft delete, no updated_at."""
    __tablename__ = "signature_audit_events"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    signature_request_id = Column(Integer, ForeignKey("signature_requests.id"),
                                  nullable=False, index=True)

    # String (not enum) — expands freely without migrations
    event_type = Column(String, nullable=False)   # created, sent, viewed, signed, declined, canceled, expired
    actor_type = Column(String, nullable=False)   # advisor, signer, system

    actor_id   = Column(Integer, nullable=True)
    actor_name = Column(String,  nullable=True)
    ip_address = Column(String,  nullable=True)
    user_agent = Column(String,  nullable=True)
    notes      = Column(Text,    nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_sig_audit_request",  "signature_request_id"),
        Index("idx_sig_audit_occurred", "occurred_at"),
    )

    def __repr__(self):
        return (
            f"<SignatureAuditEvent(id={self.id}, "
            f"request_id={self.signature_request_id}, "
            f"type='{self.event_type}', actor='{self.actor_type}')>"
        )