from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Index, Integer, SmallInteger, String,
)
from sqlalchemy.schema import CheckConstraint
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


class DocumentScope(str, PyEnum):
    CLIENT = "client"    # מסמך זהות — שייך לאדם (ת.ז., ייפוי כוח, הסכם)
    BUSINESS = "business"  # מסמך עסקי — שייך לעסק (חשבוניות, דוחות)


# מסמכים שמשויכים תמיד לאדם (לא לעסק ספציפי)
CLIENT_SCOPE_TYPES = {
    DocumentType.ID_COPY,
    DocumentType.POWER_OF_ATTORNEY,
    DocumentType.ENGAGEMENT_AGREEMENT,
}


class PermanentDocument(Base):
    """
    מסמך קבוע במערכת.
    
    scope=CLIENT: שייך לאדם — client_id חובה, business_id אסור
    scope=BUSINESS: שייך לעסק — גם client_id וגם business_id חובה
                   (client_id נשמר לשאילתות מהירות בלי JOIN)
    """
    __tablename__ = "permanent_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # בעלות
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True, index=True)
    scope = Column(pg_enum(DocumentScope), nullable=False)

    # פרטי המסמך
    document_type = Column(pg_enum(DocumentType), nullable=False)
    storage_key = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String, nullable=True)
    tax_year = Column(SmallInteger, nullable=True, index=True)

    # סטטוס
    is_present = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    status = Column(pg_enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)

    # גרסאות
    version = Column(Integer, default=1, nullable=False, server_default="1")
    superseded_by = Column(Integer, ForeignKey("permanent_documents.id"), nullable=True)

    # קישור לדוח שנתי
    annual_report_id = Column(Integer, ForeignKey("annual_reports.id"), nullable=True)

    # מטא
    notes = Column(String, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # מסמך עסקי חייב business_id
        CheckConstraint(
            "(scope = 'client') OR (scope = 'business' AND business_id IS NOT NULL)",
            name="ck_document_business_scope_requires_business_id",
        ),
        Index(
            "ix_permanent_documents_client_type_year",
            "client_id", "document_type", "tax_year",
        ),
        Index(
            "ix_permanent_documents_business",
            "business_id", "document_type", "tax_year",
        ),
    )

    def __repr__(self):
        return (
            f"<PermanentDocument(id={self.id}, client_id={self.client_id}, "
            f"business_id={self.business_id}, scope='{self.scope}', "
            f"type='{self.document_type}', status='{self.status}')>"
        )