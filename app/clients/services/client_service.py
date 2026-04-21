from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.common.enums import IdNumberType
from app.common.enums import EntityType, VatType
from app.clients.repositories.client_repository import ClientRecordView, ClientRepository
from app.clients.services.client_query_service import ClientQueryService
from app.clients.services.client_creation_service import ClientCreationService
from app.clients.services.client_lifecycle_service import ClientLifecycleService
from app.clients.services.client_update_service import ClientUpdateService
from app.clients.services.messages import (
    CLIENT_NOT_FOUND,
)
from app.core.exceptions import NotFoundError


class ClientService:
    """
    ClientRecord identity management.
    עסקים (Business) מנוהלים ב-BusinessService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self._query = ClientQueryService(db)
        self._creation = ClientCreationService(db)
        self._lifecycle = ClientLifecycleService(db)
        self._update = ClientUpdateService(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL, # type: ignore
        entity_type: Optional[EntityType] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address_street: Optional[str] = None,
        address_building_number: Optional[str] = None,
        address_apartment: Optional[str] = None,
        address_city: Optional[str] = None,
        address_zip_code: Optional[str] = None,
        vat_reporting_frequency: Optional[VatType] = None,
        vat_exempt_ceiling=None,
        advance_rate=None,
        accountant_name: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> ClientRecord:
        return self._creation.create_client(
            full_name=full_name,
            id_number=id_number,
            id_number_type=id_number_type,
            entity_type=entity_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
            accountant_name=accountant_name,
            actor_id=actor_id,
        )

    def get_client_or_raise(self, client_id: int) -> ClientRecordView:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        return client

    def update_client(self, client_id: int, actor_id: Optional[int] = None, actor_role=None, **fields) -> ClientRecordView:
        return self._update.update_client(client_id, actor_id=actor_id, actor_role=actor_role, **fields)

    def delete_client(self, client_id: int, actor_id: int) -> None:
        self._lifecycle.delete_client(client_id, actor_id)

    def restore_client(self, client_id: int, actor_id: int) -> ClientRecordView:
        return self._lifecycle.restore_client(client_id, actor_id)

    # ─── Query delegation ────────────────────────────────────────────────────

    def list_clients(self, search=None, status=None, sort_by="full_name", sort_order="asc", page=1, page_size=20):
        return self._query.list_clients(
            search=search, status=status, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
        )

    def get_client_stats(self):
        return self._query.get_client_stats()

    def list_all_clients(self):
        return self._query.list_all_clients()

    def get_conflict_info(self, id_number: str) -> dict:
        return self._query.get_conflict_info(id_number)
