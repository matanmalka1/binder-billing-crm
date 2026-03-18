from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Boolean, SmallInteger, BigInteger

from app.utils.enum_utils import pg_enum
from app.database import Base
from app.utils.time_utils import utcnow


class DocumentType(str, PyEnum):
    ID_COPY = "id_copy"
    POWER_OF_ATTORNEY = "power_of_attorney"
    ENGAGEMENT_AGREEMENT = "engagement_agreement"
    TAX_FORM = "tax_form"
    RECEIPT = "receipt"
    INVOICE_DOC = "invoice_doc"
    BANK_APPROVAL = "bank_approval"
    WITHHOLDING_CERTIFICATE = "withholding_certificate"
    NII_APPROVAL = "nii_approval"
    OTHER = "other"


class DocumentStatus(str, PyEnum):
    PENDING = "pending"
    RECEIVED = "received"
    APPROVED = "approved"
    REJECTED = "rejected"


class PermanentDocument(Base):
    __tablename__ = "permanent_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    document_type = Column(pg_enum(DocumentType), nullable=False)
    storage_key = Column(String, nullable=False)
    tax_year = Column(SmallInteger, nullable=True, index=True)
    is_present = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)

    # Extended fields
    version = Column(Integer, default=1, nullable=False, server_default="1")
    superseded_by = Column(Integer, ForeignKey("permanent_documents.id"), nullable=True)
    status = Column(pg_enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True)
    original_filename = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_permanent_documents_client_type_year", "client_id", "document_type", "tax_year"),
    )

    def __repr__(self):
        return f"<PermanentDocument(id={self.id}, client_id={self.client_id}, type='{self.document_type}', status='{self.status}')>"
