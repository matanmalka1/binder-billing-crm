from typing import BinaryIO, Optional

from sqlalchemy.orm import Session

from app.infrastructure.storage import LocalStorageProvider, StorageProvider
from app.permanent_documents.models.permanent_document import DocumentType, PermanentDocument
from app.clients.repositories.client_repository import ClientRepository
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


class PermanentDocumentService:
    """Permanent document management service for Sprint 4."""

    def __init__(self, db: Session, storage: Optional[StorageProvider] = None):
        self.db = db
        self.document_repo = PermanentDocumentRepository(db)
        self.client_repo = ClientRepository(db)
        self.storage = storage or LocalStorageProvider()

    def upload_document(
        self,
        client_id: int,
        document_type: DocumentType,
        file_data: BinaryIO,
        filename: str,
        uploaded_by: int,
    ) -> PermanentDocument:
        """
        Upload permanent document.
        
        Rules:
        - Valid client required
        - Valid document type required
        - Stores in cloud storage
        - Marks is_present = True
        
        Raises:
            ValueError: If client not found or document type invalid
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Generate storage key
        storage_key = f"clients/{client_id}/{document_type.value}/{filename}"

        # Upload to storage
        self.storage.upload(storage_key, file_data, "application/octet-stream")

        # Create document record
        document = self.document_repo.create(
            client_id=client_id,
            document_type=document_type,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
        )

        return document

    def list_client_documents(self, client_id: int) -> list[PermanentDocument]:
        """List all permanent documents for a client."""
        return self.document_repo.list_by_client(client_id)

    def get_missing_document_types(self, client_id: int) -> list[DocumentType]:
        """
        Get list of missing document types for a client.
        
        Operational signal: advisory only.
        """
        existing_docs = self.document_repo.list_by_client(client_id)
        existing_types = {doc.document_type for doc in existing_docs}

        all_types = {DocumentType.ID_COPY, DocumentType.POWER_OF_ATTORNEY, DocumentType.ENGAGEMENT_AGREEMENT}
        missing_types = all_types - existing_types

        return list(missing_types)
