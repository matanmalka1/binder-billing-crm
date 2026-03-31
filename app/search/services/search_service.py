from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository
from app.clients.repositories.client_repository import ClientRepository
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
        self.client_repo = ClientRepository(db)
        self.binder_repo = BinderRepository(db)

    def search(
        self,
        query: Optional[str] = None,
        client_name: Optional[str] = None,
        id_number: Optional[str] = None,
        binder_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int, list[dict]]:
        documents: list[dict] = (
            DocumentSearchService(self.db).search_documents(query) if query else []
        )

        # --- Client search: DB-level filtering ---
        if query or client_name or id_number:
            if not binder_number:
                clients, total = self.client_repo.search(
                    query=query,
                    client_name=client_name,
                    id_number=id_number,
                    page=page,
                    page_size=page_size,
                )
                binder_map = self.binder_repo.map_active_by_clients([c.id for c in clients])
                return [
                    {
                        "result_type": "client",
                        "client_id": c.id,
                        "client_name": c.full_name,
                        "id_number": c.id_number,
                        "client_status": None,
                        "binder_id": binder_map[c.id].id if c.id in binder_map else None,
                        "binder_number": binder_map[c.id].binder_number if c.id in binder_map else None,
                    }
                    for c in clients
                ], total, documents

        # --- Mixed / binder-number search: build full result set then paginate ---
        # Bounded by _MIXED_SEARCH_*_LIMIT. Results beyond ceiling are excluded.
        results: list[dict] = []

        if query or client_name or id_number:
            all_clients, _ = self.client_repo.search(
                query=query,
                client_name=client_name,
                id_number=id_number,
                page=1,
                page_size=_MIXED_SEARCH_CLIENT_LIMIT,
            )
            client_binder_map = self.binder_repo.map_active_by_clients([c.id for c in all_clients])
            for c in all_clients:
                b = client_binder_map.get(c.id)
                results.append(
                    {
                        "result_type": "client",
                        "client_id": c.id,
                        "client_name": c.full_name,
                        "id_number": c.id_number,
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
            binder_client_ids = [b.client_id for b in binders]
            binder_client_map = {c.id: c for c in self.client_repo.list_by_ids(binder_client_ids)}
            for binder in binders:
                client = binder_client_map.get(binder.client_id)
                results.append(
                    {
                        "result_type": "binder",
                        "client_id": binder.client_id,
                        "client_name": client.full_name if client else "לא ידוע",
                        "id_number": client.id_number if client else None,
                        "client_status": None,
                        "binder_id": binder.id,
                        "binder_number": binder.binder_number,
                    }
                )

        total = len(results)
        offset = (page - 1) * page_size
        return results[offset: offset + page_size], total, documents
