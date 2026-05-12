from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.schemas.client_record_response import (
    ClientRecordListResponse,
    ClientRecordResponse,
)
from app.clients.services.client_query_service import ClientQueryService
from app.clients.services.client_creation_service import ClientCreationService
from app.clients.services.client_lifecycle_service import ClientLifecycleService
from app.clients.services.client_update_service import ClientUpdateService
from app.clients.services.messages import CLIENT_NOT_FOUND
from app.core.exceptions import NotFoundError


class ClientService:
    """
    ClientRecord identity management.
    עסקים (Business) מנוהלים ב-BusinessService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.record_repo = ClientRecordRepository(db)
        self._query = ClientQueryService(db)
        self._creation = ClientCreationService(db)
        self._lifecycle = ClientLifecycleService(db)
        self._update = ClientUpdateService(db)

    def create_client(self, **kwargs) -> ClientRecord:
        return self._creation.create_client(**kwargs)

    def get_client_or_raise(self, client_id: int) -> ClientRecord:
        client = self.record_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(
                CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND"
            )
        return client

    def update_client(
        self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields
    ) -> dict:
        return self._update.update_client(
            client_id, actor_id=actor_id, actor_role=actor_role, **fields
        )

    def delete_client(self, client_id: int, actor_id: int) -> None:
        self._lifecycle.delete_client(client_id, actor_id)

    def restore_client(self, client_id: int, actor_id: int) -> dict:
        return self._lifecycle.restore_client(client_id, actor_id)

    # ─── Query delegation ────────────────────────────────────────────────────

    def get_client_stats(self):
        return self._query.get_client_stats()

    def list_all_clients(self):
        return self._query.list_all_clients()

    def get_conflict_info(self, id_number: str):
        return self._query.get_conflict_info(id_number)

    def get_full_client(self, client_id: int, tax_year=None) -> ClientRecordResponse:
        return self._query.get_full_client(client_id, tax_year=tax_year)

    def get_full_client_including_deleted(self, client_id: int) -> ClientRecordResponse:
        return self._query.get_full_client_including_deleted(client_id)

    def list_full_clients(
        self,
        search=None,
        status=None,
        accountant_id=None,
        entity_type=None,
        tax_year=None,
        sort_by="official_name",
        sort_order="asc",
        page=1,
        page_size=20,
    ) -> ClientRecordListResponse:
        return self._query.list_full_clients(
            search=search,
            status=status,
            accountant_id=accountant_id,
            entity_type=entity_type,
            tax_year=tax_year,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
