from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository
from app.search.schemas.search import DocumentSearchResult

_DOCUMENT_SEARCH_LIMIT = 50


class DocumentSearchService:
    """Searches permanent documents by filename or type."""

    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = PermanentDocumentRepository(db)
        self.business_repo = BusinessRepository(db)

    def search_documents(self, query: str) -> list[DocumentSearchResult]:
        docs = self.doc_repo.search_by_query(query, limit=_DOCUMENT_SEARCH_LIMIT)
        business_cache: dict[int, str] = {}
        results = []
        for doc in docs:
            if doc.business_id not in business_cache:
                business = self.business_repo.get_by_id(doc.business_id)
                business_cache[doc.business_id] = business.full_name if business else "לא ידוע"
            results.append(DocumentSearchResult(
                id=doc.id,
                client_id=doc.client_id,
                business_id=doc.business_id,
                business_name=business_cache[doc.business_id],
                document_type=doc.document_type,
                original_filename=doc.original_filename,
                tax_year=doc.tax_year,
                status=doc.status,
            ))
        return results
