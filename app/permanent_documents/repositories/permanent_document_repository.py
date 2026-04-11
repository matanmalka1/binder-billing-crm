from typing import Optional

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from app.permanent_documents.models.permanent_document import DocumentScope, DocumentStatus, PermanentDocument


class PermanentDocumentRepository:
    """Data access layer for PermanentDocument entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        business_id: Optional[int],
        scope: DocumentScope,
        document_type: str,
        storage_key: str,
        uploaded_by: int,
        tax_year: Optional[int] = None,
        version: int = 1,
        status: DocumentStatus = DocumentStatus.PENDING,
        annual_report_id: Optional[int] = None,
        original_filename: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
        notes: Optional[str] = None,
        commit: bool = True,
    ) -> PermanentDocument:
        document = PermanentDocument(
            client_id=client_id,
            business_id=business_id,
            scope=scope,
            document_type=document_type,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            tax_year=tax_year,
            is_present=True,
            version=version,
            status=status,
            annual_report_id=annual_report_id,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            notes=notes,
        )
        self.db.add(document)
        if commit:
            self.db.commit()
            self.db.refresh(document)
        else:
            self.db.flush()
        return document

    def get_by_id(self, document_id: int) -> Optional[PermanentDocument]:
        return (
            self.db.query(PermanentDocument)
            .filter(
                PermanentDocument.id == document_id,
                PermanentDocument.is_deleted == False,  # noqa: E712
            )
            .first()
        )

    def list_by_business(
        self,
        business_id: int,
        tax_year: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        include_superseded: bool = False,
    ) -> list[PermanentDocument]:
        q = self.db.query(PermanentDocument).filter(
            PermanentDocument.business_id == business_id,
            PermanentDocument.is_deleted == False,  # noqa: E712
        )
        if not include_superseded:
            q = q.filter(PermanentDocument.superseded_by == None)  # noqa: E711
        if tax_year is not None:
            q = q.filter(PermanentDocument.tax_year == tax_year)
        if document_type is not None:
            q = q.filter(PermanentDocument.document_type == document_type)
        if status is not None:
            q = q.filter(PermanentDocument.status == status)
        return q.order_by(PermanentDocument.uploaded_at.desc()).all()

    def list_by_client(
        self,
        client_id: int,
        tax_year: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        include_superseded: bool = False,
    ) -> list[PermanentDocument]:
        q = self.db.query(PermanentDocument).filter(
            PermanentDocument.client_id == client_id,
            PermanentDocument.is_deleted == False,  # noqa: E712
        )
        if not include_superseded:
            q = q.filter(PermanentDocument.superseded_by == None)  # noqa: E711
        if tax_year is not None:
            q = q.filter(PermanentDocument.tax_year == tax_year)
        if document_type is not None:
            q = q.filter(PermanentDocument.document_type == document_type)
        if status is not None:
            q = q.filter(PermanentDocument.status == status)
        return q.order_by(PermanentDocument.uploaded_at.desc()).all()

    def count_by_business(self, business_id: int) -> int:
        return (
            self.db.query(PermanentDocument)
            .filter(
                PermanentDocument.business_id == business_id,
                PermanentDocument.is_deleted == False,  # noqa: E712
            )
            .count()
        )

    def search_by_query(self, query: str, limit: int = 50) -> list[PermanentDocument]:
        term = f"%{query.strip()}%"
        return (
            self.db.query(PermanentDocument)
            .filter(
                PermanentDocument.is_deleted == False,  # noqa: E712
                PermanentDocument.superseded_by == None,  # noqa: E711
                (
                    PermanentDocument.original_filename.ilike(term)
                    | cast(PermanentDocument.document_type, String).ilike(term)
                ),
            )
            .order_by(PermanentDocument.uploaded_at.desc())
            .limit(limit)
            .all()
        )
