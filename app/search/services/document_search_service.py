from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_read_repository import get_full_records_bulk
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
        client_map = get_full_records_bulk(self.db, [doc.client_record_id for doc in docs])
        results = []
        for doc in docs:
            if doc.business_id and doc.business_id not in business_cache:
                business = self.business_repo.get_by_id(doc.business_id)
                business_cache[doc.business_id] = business.full_name if business else "לא ידוע"
            client = client_map.get(doc.client_record_id)
            results.append(DocumentSearchResult(
                id=doc.id,
                client_record_id=doc.client_record_id,
                office_client_number=client["office_client_number"] if client else None,
                client_name=client["full_name"] if client else "לא ידוע",
                business_id=doc.business_id,
                business_name=business_cache.get(doc.business_id),
                document_type=doc.document_type,
                original_filename=doc.original_filename,
                tax_year=doc.tax_year,
                status=doc.status,
            ))
        return results

    def list_client_documents(self, client_record_id: int, query: str) -> list[DocumentSearchResult]:
        docs = self.doc_repo.list_by_client_record(client_record_id)
        term = query.strip().lower()
        client_map = get_full_records_bulk(self.db, [client_record_id])
        client = client_map.get(client_record_id)
        return [
            DocumentSearchResult(
                id=doc.id,
                client_record_id=doc.client_record_id,
                office_client_number=client["office_client_number"] if client else None,
                client_name=client["full_name"] if client else "לא ידוע",
                business_id=doc.business_id,
                business_name=(self.business_repo.get_by_id(doc.business_id).full_name if doc.business_id and self.business_repo.get_by_id(doc.business_id) else None),
                document_type=doc.document_type,
                original_filename=doc.original_filename,
                tax_year=doc.tax_year,
                status=doc.status,
            )
            for doc in docs
            if term in (doc.original_filename or "").lower() or term in str(doc.document_type).lower()
        ]
