from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean

from app.database import Base
from app.utils.time import utcnow


class DocumentType(str, PyEnum):
    ID_COPY = "id_copy"
    POWER_OF_ATTORNEY = "power_of_attorney"
    ENGAGEMENT_AGREEMENT = "engagement_agreement"


class PermanentDocument(Base):
    __tablename__ = "permanent_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType), nullable=False)
    storage_key = Column(String, nullable=False)
    is_present = Column(Boolean, default=True, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return f"<PermanentDocument(id={self.id}, client_id={self.client_id}, type='{self.document_type}', is_present={self.is_present})>"
