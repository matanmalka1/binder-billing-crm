from typing import Optional

from sqlalchemy.orm import Session

from app.models import PermanentDocument, DocumentType


class PermanentDocumentRepository:
    """Data access layer for PermanentDocument entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        document_type: DocumentType,
        storage_key: str,
        uploaded_by: int,
    ) -> PermanentDocument:
        """Create new permanent document record."""
        document = PermanentDocument(
            client_id=client_id,
            document_type=document_type,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            is_present=True,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: int) -> Optional[PermanentDocument]:
        """Retrieve document by ID."""
        return self.db.query(PermanentDocument).filter(PermanentDocument.id == document_id).first()

    def list_by_client(self, client_id: int) -> list[PermanentDocument]:
        """List all permanent documents for a client."""
        return (
            self.db.query(PermanentDocument)
            .filter(PermanentDocument.client_id == client_id)
            .order_by(PermanentDocument.uploaded_at.desc())
            .all()
        )

    def count_by_client(self, client_id: int) -> int:
        """Count permanent documents for a client."""
        return self.db.query(PermanentDocument).filter(PermanentDocument.client_id == client_id).count()
