from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.search.schemas.search import DocumentSearchResult
from app.search.services.document_search_service import DocumentSearchService

# Safety ceiling for mixed searches that must be resolved in memory.
# Pure client-only searches already use DB-level pagination and are not affected.
# Known architectural debt — see CLAUDE.md.
_MIXED_SEARCH_BINDER_LIMIT = 1000
_MIXED_SEARCH_CLIENT_LIMIT = 500


class SearchService:
    """Unified search for clients and binders."""

    def __init__(self, db: Session):
        self.db = db
        self.client_record_repo = ClientRecordRepository(db)
        self.legal_entity_repo = LegalEntityRepository(db)
        self.business_repo = BusinessRepository(db)
        self.binder_repo = BinderRepository(db)

    def _legal_entity_map(self, legal_entity_ids: list[int]) -> dict[int, object]:
        return {
            legal_id: self.legal_entity_repo.get_by_id(legal_id)
            for legal_id in set(legal_entity_ids)
        }

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        binder_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int, list[DocumentSearchResult]]:
        documents: list[DocumentSearchResult] = (
            DocumentSearchService(self.db).search_documents(query) if query else []
        )

        # --- Client search: DB-level filtering ---
        if query or client_name or id_number:
            if not binder_number:
                records, total = self.client_record_repo.search(
                    query=query,
                    client_name=client_name,
                    id_number=id_number,
                    page=page,
                    page_size=page_size,
                )
                legal_map = self._legal_entity_map([record.legal_entity_id for record in records])
                binder_map = self.binder_repo.map_active_by_clients([record.id for record in records])
                return [
                    {
                        "result_type": "client",
                        "client_id": record.id,
                        "office_client_number": record.office_client_number,
                        "client_name": legal_map[record.legal_entity_id].official_name if legal_map.get(record.legal_entity_id) else "לא ידוע",
                        "id_number": legal_map[record.legal_entity_id].id_number if legal_map.get(record.legal_entity_id) else None,
                        "client_status": None,
                        "binder_id": binder_map[record.id].id if record.id in binder_map else None,
                        "binder_number": binder_map[record.id].binder_number if record.id in binder_map else None,
                    }
                    for record in records
                ], total, documents

        # --- Mixed / binder-number search: build full result set then paginate ---
        # Bounded by _MIXED_SEARCH_*_LIMIT. Results beyond ceiling are excluded.
        results: list[dict] = []

        if query or client_name or id_number:
            all_records, _ = self.client_record_repo.search(
                query=query,
                client_name=client_name,
                id_number=id_number,
                page=1,
                page_size=_MIXED_SEARCH_CLIENT_LIMIT,
            )
            legal_map = self._legal_entity_map([record.legal_entity_id for record in all_records])
            client_binder_map = self.binder_repo.map_active_by_clients([record.id for record in all_records])
            for record in all_records:
                b = client_binder_map.get(record.id)
                legal_entity = legal_map.get(record.legal_entity_id)
                results.append(
                    {
                        "result_type": "client",
                        "client_id": record.id,
                        "office_client_number": record.office_client_number,
                        "client_name": legal_entity.official_name if legal_entity else "לא ידוע",
                        "id_number": legal_entity.id_number if legal_entity else None,
                        "client_status": None,
                        "binder_id": b.id if b else None,
                        "binder_number": b.binder_number if b else None,
                    }
                )

        if query or binder_number:
            db_binder_number = binder_number or (query if not (client_name or id_number) else None)
            binders = self.binder_repo.list_active(
                binder_number=db_binder_number,
                page=1,
                page_size=_MIXED_SEARCH_BINDER_LIMIT,
            )
            binder_cr_ids = [b.client_record_id for b in binders]
            records = {record.id: record for record in self.client_record_repo.list_by_ids(binder_cr_ids)}
            cr_to_legal = {record.id: record.legal_entity_id for record in records.values()}
            legal_map = self._legal_entity_map(list(cr_to_legal.values()))
            businesses = self.business_repo.list_by_legal_entity_ids(legal_entity_ids)
            legal_to_business = {b.legal_entity_id: b for b in businesses}
            for binder in binders:
                record = records.get(binder.client_record_id)
                legal_id = cr_to_legal.get(binder.client_record_id)
                business = legal_to_business.get(legal_id) if legal_id else None
                legal_entity = legal_map.get(legal_id) if legal_id else None
                results.append(
                    {
                        "result_type": "binder",
                        "client_id": binder.client_record_id,
                        "office_client_number": record.office_client_number if record else None,
                        "client_name": business.full_name if business else (legal_entity.official_name if legal_entity else "לא ידוע"),
                        "id_number": legal_entity.id_number if legal_entity else None,
                        "client_status": None,
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                    }
                )

        total = len(results)
        offset = (page - 1) * page_size
        return results[offset: offset + page_size], total, documents
