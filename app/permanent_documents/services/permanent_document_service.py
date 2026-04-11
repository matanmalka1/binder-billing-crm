from typing import BinaryIO, Optional
import mimetypes
import io

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.clients.services.client_service import ClientService
from app.permanent_documents.services.upload_constraints import _ALLOWED_MIME_TYPES, _MAX_FILE_SIZE
from app.infrastructure.storage import StorageProvider, get_storage_provider
from app.permanent_documents.models.permanent_document import (
    CLIENT_SCOPE_TYPES,
    DocumentScope,
    DocumentStatus,
    DocumentType,
    PermanentDocument,
)
from app.utils.time_utils import utcnow
from app.businesses.services.business_lookup import get_business_or_raise
from app.binders.services.signals_service import SignalsService
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
        self.storage = storage or get_storage_provider()

    def _resolve_mime(self, mime_type: Optional[str], filename: str) -> str:
        resolved = mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if resolved not in _ALLOWED_MIME_TYPES:
            raise AppError(
                "סוג הקובץ אינו נתמך. מותר: PDF, Word, Excel, תמונות",
                "DOCUMENT.INVALID_FILE_TYPE",
                status_code=422,
            )
        return resolved

    def upload_document(
        self,
        business_id: int,
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
            business = get_business_or_raise(self.db, business_id)
        except NotFoundError as exc:
            raise NotFoundError("העסק לא נמצא", "PERMANENT_DOCUMENTS.CLIENT_NOT_FOUND") from exc

        client_id = business.client_id
        doc_type_enum = DocumentType(document_type)
        scope = DocumentScope.CLIENT if doc_type_enum in CLIENT_SCOPE_TYPES else DocumentScope.BUSINESS

        file_bytes = file_data.read()
        file_size = len(file_bytes)
        if file_size > _MAX_FILE_SIZE:
            raise AppError(
                f"גודל הקובץ חורג מהמותר (מקסימום {_MAX_FILE_SIZE // (1024 * 1024)}MB)",
                "DOCUMENT.FILE_TOO_LARGE",
                status_code=422,
            )
        resolved_mime = self._resolve_mime(mime_type, filename)

        tax_year_str = str(tax_year) if tax_year else "permanent"
        existing = self.query_repo.get_latest_version(business_id, document_type, tax_year)
        next_version = (existing.version + 1) if existing else 1
        storage_key = f"businesses/{business_id}/{document_type}/{tax_year_str}/v{next_version}_{filename}"

        # Flush DB record first; upload to storage only if flush succeeds.
        # Single commit at the end keeps record + superseded_by atomic.
        document = self.document_repo.create(
            client_id=client_id,
            business_id=business_id,
            scope=scope,
            document_type=document_type,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            tax_year=tax_year,
            version=next_version,
            status=DocumentStatus.APPROVED,
            annual_report_id=annual_report_id,
            original_filename=filename,
            file_size_bytes=file_size,
            mime_type=resolved_mime,
            notes=notes,
            commit=False,
        )
        document.approved_by = uploaded_by
        document.approved_at = utcnow()
        try:
            self.storage.upload(storage_key, io.BytesIO(file_bytes), resolved_mime)
        except Exception as exc:
            self.db.rollback()
            raise AppError("העלאת הקובץ נכשלה", "DOCUMENT.UPLOAD_FAILED", status_code=500) from exc

        if existing:
            existing.superseded_by = document.id
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise AppError(
                "גרסה זו של המסמך כבר קיימת, נסה שוב",
                "DOCUMENT.VERSION_CONFLICT",
                status_code=409,
            )
        self.db.refresh(document)
        return document

    def get_download_url(self, document_id: int, expires_in: int = 3600) -> str:
        doc = self.document_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        return self.storage.get_presigned_url(doc.storage_key, expires_in=expires_in)

    def list_business_documents(
        self,
        business_id: int,
        tax_year: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
    ) -> list[PermanentDocument]:
        return self.document_repo.list_by_business(
            business_id,
            tax_year=tax_year,
            document_type=document_type,
            status=status,
        )

    def list_client_documents(
        self,
        client_id: int,
        tax_year: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
    ) -> list[PermanentDocument]:
        ClientService(self.db).get_client_or_raise(client_id)
        return self.document_repo.list_by_client(
            client_id,
            tax_year=tax_year,
            document_type=document_type,
            status=status,
        )

    def get_missing_document_types(
        self, business_id: int, required: Optional[list[str]] = None
    ) -> list[str]:
        business = get_business_or_raise(self.db, business_id)
        required_types = required if required is not None else _DEFAULT_REQUIRED_TYPES
        return self.query_repo.missing_by_type(business_id, business.client_id, required_types)

    def get_operational_signals(self, business_id: int) -> dict:
        return SignalsService(self.db).compute_business_operational_signals(business_id)

    def get_client_operational_signals(self, client_id: int) -> dict:
        ClientService(self.db).get_client_or_raise(client_id)
        return {
            "client_id": client_id,
            "missing_documents": self.query_repo.missing_by_client_type(client_id, _DEFAULT_REQUIRED_TYPES),
        }

    def delete_document(self, document_id: int) -> None:
        doc = self.document_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")
        doc.is_deleted = True
        self.db.commit()

    def replace_document(
        self,
        document_id: int,
        file_data: BinaryIO,
        filename: str,
        uploaded_by: int,
        mime_type: str | None = None,
    ) -> PermanentDocument:
        doc = self.document_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("המסמך לא נמצא", "PERMANENT_DOCUMENTS.NOT_FOUND")

        file_bytes = file_data.read()
        file_size = len(file_bytes)
        if file_size > _MAX_FILE_SIZE:
            raise AppError(
                f"גודל הקובץ חורג מהמותר (מקסימום {_MAX_FILE_SIZE // (1024 * 1024)}MB)",
                "DOCUMENT.FILE_TOO_LARGE",
                status_code=422,
            )
        resolved_mime = self._resolve_mime(mime_type, filename)

        tax_year_str = str(doc.tax_year) if doc.tax_year else "permanent"
        next_version = doc.version + 1
        storage_key = f"businesses/{doc.business_id}/{doc.document_type}/{tax_year_str}/v{next_version}_{filename}"
        self.storage.upload(storage_key, io.BytesIO(file_bytes), resolved_mime)
        doc.storage_key = storage_key
        doc.mime_type = resolved_mime
        doc.file_size_bytes = file_size
        doc.original_filename = filename
        doc.uploaded_at = utcnow()
        doc.uploaded_by = uploaded_by
        doc.is_present = True
        doc.version = next_version
        self.db.commit()
        self.db.refresh(doc)
        return doc
