from datetime import datetime
from typing import BinaryIO, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.infrastructure.storage import StorageProvider, get_storage_provider
from app.permanent_documents.models.permanent_document import DocumentType, PermanentDocument
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import get_client_or_raise
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


class PermanentDocumentService:
    """Permanent document management service."""

    def __init__(self, db: Session, storage: Optional[StorageProvider] = None):
        self.db = db
        self.document_repo = PermanentDocumentRepository(db)
        self.client_repo = ClientRepository(db)
        self.storage = storage or get_storage_provider()

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
        - Stores in cloud storage (R2) or local (dev/test)
        - Marks is_present = True

        Raises:
            ValueError: If client not found or document type invalid
        """
        try:
            get_client_or_raise(self.client_repo, client_id)
        except NotFoundError as exc:
            raise NotFoundError(str(exc), "PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND") from exc

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

    def get_download_url(self, document_id: int, expires_in: int = 3600) -> str:
        """
        Generate a presigned download URL for a document.

        Args:
            document_id: Document ID
            expires_in: URL expiry in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            HTTPException 404: If document not found or deleted
        """
        doc = self.document_repo.get_by_id(document_id)
        if not doc or doc.is_deleted:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        return self.storage.get_presigned_url(doc.storage_key, expires_in=expires_in)

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

    def delete_document(self, document_id: int) -> None:
        """Soft-delete a document (set is_deleted=True). Raises 404 if not found."""
        doc = self.document_repo.get_by_id(document_id)
        if not doc or doc.is_deleted:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        doc.is_deleted = True
        self.db.commit()

    def replace_document(
        self,
        document_id: int,
        file_data: BinaryIO,
        filename: str,
        uploaded_by: int,
    ) -> PermanentDocument:
        """Replace file for an existing document. Raises 404 if not found or deleted."""
        doc = self.document_repo.get_by_id(document_id)
        if not doc or doc.is_deleted:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        storage_key = f"clients/{doc.client_id}/{doc.document_type.value}/{filename}"
        self.storage.upload(storage_key, file_data, "application/octet-stream")
        doc.storage_key = storage_key
        doc.uploaded_at = datetime.utcnow()
        doc.uploaded_by = uploaded_by
        doc.is_present = True
        self.db.commit()
        self.db.refresh(doc)
        return doc
