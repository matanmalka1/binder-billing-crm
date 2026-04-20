from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.permanent_documents.models.permanent_document import PermanentDocument
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.permanent_documents.repositories.permanent_document_query_repository import PermanentDocumentQueryRepository
from app.permanent_documents.services.messages import DOCUMENT_NOT_FOUND_ERROR


class PermanentDocumentActionService:
    def __init__(self, db: Session):
        self.db = db
        self.document_repo = PermanentDocumentRepository(db)
        self.query_repo = PermanentDocumentQueryRepository(db)

    def _get_or_raise(self, document_id: int) -> PermanentDocument:
        doc = self.document_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(DOCUMENT_NOT_FOUND_ERROR, "PERMANENT_DOCUMENTS.NOT_FOUND")
        return doc

    def get_document_versions(
        self, client_record_id: int, document_type: str, tax_year: Optional[int] = None
    ) -> list[PermanentDocument]:
        client_record_id = ClientRecordRepository(self.db).get_by_id(client_record_id).id
        return self.query_repo.get_all_versions_by_client_record(client_record_id, document_type, tax_year)

    def update_notes(self, document_id: int, notes: str) -> PermanentDocument:
        doc = self._get_or_raise(document_id)
        doc.notes = notes
        self.db.flush()
        return doc

    def list_by_annual_report(self, annual_report_id: int) -> list[PermanentDocument]:
        return self.query_repo.list_by_annual_report(annual_report_id)
