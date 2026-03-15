from sqlalchemy.orm import Session

from app.clients.repositories.client_repository import ClientRepository
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository

_DOCUMENT_SEARCH_LIMIT = 50


class DocumentSearchService:
    """Searches permanent documents by filename or type."""

    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = PermanentDocumentRepository(db)
        self.client_repo = ClientRepository(db)

    def search_documents(self, query: str) -> list[dict]:
        docs = self.doc_repo.search_by_query(query, limit=_DOCUMENT_SEARCH_LIMIT)
        results = []
        client_cache: dict[int, str] = {}
        for doc in docs:
            if doc.client_id not in client_cache:
                client = self.client_repo.get_by_id(doc.client_id)
                client_cache[doc.client_id] = client.full_name if client else "Unknown"
            results.append(
                {
                    "id": doc.id,
                    "client_id": doc.client_id,
                    "client_name": client_cache[doc.client_id],
                    "document_type": doc.document_type,
                    "original_filename": doc.original_filename,
                    "tax_year": doc.tax_year,
                    "status": doc.status,
                }
            )
        return results
