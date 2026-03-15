from typing import BinaryIO, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.infrastructure.storage import StorageProvider, get_storage_provider
from app.permanent_documents.models.permanent_document import DocumentStatus, DocumentType, PermanentDocument
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_lookup import get_client_or_raise
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.permanent_documents.repositories.permanent_document_query_repository import PermanentDocumentQueryRepository
from app.utils.time_utils import utcnow

_DEFAULT_REQUIRED_TYPES = [
    DocumentType.ID_COPY.value,
    DocumentType.POWER_OF_ATTORNEY.value,
    DocumentType.ENGAGEMENT_AGREEMENT.value,
]


class PermanentDocumentService:
    """Permanent document management service."""

    def __init__(self, db: Session, storage: Optional[StorageProvider] = None):
        self.db = db
        self.document_repo = PermanentDocumentRepository(db)
        self.query_repo = PermanentDocumentQueryRepository(db)
        self.client_repo = ClientRepository(db)
        self.storage = storage or get_storage_provider()

    def upload_document(
        self,
        client_id: int,
        document_type: str,
        file_data: BinaryIO,
        filename: str,
        uploaded_by: int,
        tax_year: Optional[int] = None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> PermanentDocument:
        try:
            get_client_or_raise(self.db, client_id)
        except NotFoundError as exc:
            raise NotFoundError(str(exc), "PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND") from exc

        tax_year_str = str(tax_year) if tax_year else "permanent"
        existing = self.query_repo.get_latest_version(client_id, document_type, tax_year)
        next_version = (existing.version + 1) if existing else 1

        file_bytes = file_data.read()
        file_size = len(file_bytes)
        import io
        file_data = io.BytesIO(file_bytes)

        storage_key = f"clients/{client_id}/{document_type}/{tax_year_str}/v{next_version}_{filename}"
        self.storage.upload(storage_key, file_data, mime_type or "application/octet-stream")

        if existing:
            existing.superseded_by = None  # will be set after new doc created
            self.db.flush()

        document = self.document_repo.create(
            client_id=client_id,
            document_type=document_type,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            tax_year=tax_year,
            version=next_version,
            annual_report_id=annual_report_id,
            original_filename=filename,
            file_size_bytes=file_size,
            mime_type=mime_type or "application/octet-stream",
            notes=notes,
        )

        if existing:
            existing.superseded_by = document.id
            self.db.commit()

        return document

    def get_download_url(self, document_id: int, expires_in: int = 3600) -> str:
        doc = self.document_repo.get_by_id(document_id)
        if not doc or doc.is_deleted:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        return self.storage.get_presigned_url(doc.storage_key, expires_in=expires_in)

    def list_client_documents(
        self,
        client_id: int,
        tax_year: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
    ) -> list[PermanentDocument]:
        return self.document_repo.list_by_client(
            client_id,
            tax_year=tax_year,
            document_type=document_type,
            status=status,
        )

    def get_missing_document_types(
        self, client_id: int, required: Optional[list[str]] = None
    ) -> list[str]:
        required_types = required if required is not None else _DEFAULT_REQUIRED_TYPES
        return self.query_repo.missing_by_type(client_id, required_types)

    def delete_document(self, document_id: int) -> None:
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
        doc = self.document_repo.get_by_id(document_id)
        if not doc or doc.is_deleted:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        tax_year_str = str(doc.tax_year) if doc.tax_year else "permanent"
        next_version = doc.version + 1
        storage_key = f"clients/{doc.client_id}/{doc.document_type}/{tax_year_str}/v{next_version}_{filename}"
        self.storage.upload(storage_key, file_data, doc.mime_type or "application/octet-stream")
        doc.storage_key = storage_key
        doc.uploaded_at = utcnow()
        doc.uploaded_by = uploaded_by
        doc.is_present = True
        doc.version = next_version
        self.db.commit()
        self.db.refresh(doc)
        return doc
