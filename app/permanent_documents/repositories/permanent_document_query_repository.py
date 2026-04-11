from typing import Optional

from sqlalchemy.orm import Session

from app.permanent_documents.models.permanent_document import PermanentDocument


class PermanentDocumentQueryRepository:
    """Read-only query repository for advanced document lookups."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_version(
        self,
        client_id: int,
        document_type: str,
        tax_year: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> Optional[PermanentDocument]:
        q = self.db.query(PermanentDocument).filter(
            PermanentDocument.client_id == client_id,
            PermanentDocument.document_type == document_type,
            PermanentDocument.is_deleted == False,  # noqa: E712
            PermanentDocument.superseded_by == None,  # noqa: E711
        )
        if business_id is None:
            q = q.filter(PermanentDocument.business_id == None)  # noqa: E711
        else:
            q = q.filter(PermanentDocument.business_id == business_id)
        if tax_year is not None:
            q = q.filter(PermanentDocument.tax_year == tax_year)
        return q.order_by(PermanentDocument.version.desc()).first()

    def get_all_versions(
        self, business_id: int, document_type: str, tax_year: Optional[int] = None
    ) -> list[PermanentDocument]:
        q = self.db.query(PermanentDocument).filter(
            PermanentDocument.business_id == business_id,
            PermanentDocument.document_type == document_type,
            PermanentDocument.is_deleted == False,  # noqa: E712
        )
        if tax_year is not None:
            q = q.filter(PermanentDocument.tax_year == tax_year)
        return q.order_by(PermanentDocument.version.desc()).all()

    def get_all_versions_by_client(
        self, client_id: int, document_type: str, tax_year: Optional[int] = None
    ) -> list[PermanentDocument]:
        q = self.db.query(PermanentDocument).filter(
            PermanentDocument.client_id == client_id,
            PermanentDocument.document_type == document_type,
            PermanentDocument.is_deleted == False,  # noqa: E712
        )
        if tax_year is not None:
            q = q.filter(PermanentDocument.tax_year == tax_year)
        return q.order_by(PermanentDocument.version.desc()).all()

    def list_by_annual_report(self, annual_report_id: int) -> list[PermanentDocument]:
        return (
            self.db.query(PermanentDocument)
            .filter(
                PermanentDocument.annual_report_id == annual_report_id,
                PermanentDocument.is_deleted == False,  # noqa: E712
            )
            .order_by(PermanentDocument.uploaded_at.desc())
            .all()
        )

    def missing_by_type(
        self, business_id: int, client_id: int, required_types: list[str]
    ) -> list[str]:
        existing = (
            self.db.query(PermanentDocument.document_type)
            .filter(
                (
                    (PermanentDocument.business_id == business_id)
                    | (PermanentDocument.client_id == client_id)
                ),
                PermanentDocument.is_deleted == False,  # noqa: E712
                PermanentDocument.superseded_by == None,  # noqa: E711
            )
            .distinct()
            .all()
        )
        existing_types = {row[0] for row in existing}
        return [t for t in required_types if t not in existing_types]

    def missing_by_client_type(self, client_id: int, required_types: list[str]) -> list[str]:
        existing = (
            self.db.query(PermanentDocument.document_type)
            .filter(
                PermanentDocument.client_id == client_id,
                PermanentDocument.is_deleted == False,  # noqa: E712
                PermanentDocument.superseded_by == None,  # noqa: E711
            )
            .distinct()
            .all()
        )
        existing_types = {row[0] for row in existing}
        return [t for t in required_types if t not in existing_types]
