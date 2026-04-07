import json
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.audit.constants import ACTION_CREATED, ACTION_DELETED, ACTION_RESTORED, ACTION_UPDATED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.clients.models.client import Client, IdNumberType
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.client_binder_helper import create_initial_binder
from app.clients.services.client_query_service import ClientQueryService
from app.core.exceptions import ConflictError, NotFoundError


class ClientService:
    """
    Client identity management.
    עסקים (Business) מנוהלים ב-BusinessService.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)
        self._query = ClientQueryService(db)

    def create_client(
        self,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType = IdNumberType.INDIVIDUAL,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address_street: Optional[str] = None,
        address_building_number: Optional[str] = None,
        address_apartment: Optional[str] = None,
        address_city: Optional[str] = None,
        address_zip_code: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> Client:
        active_clients = self.client_repo.get_active_by_id_number(id_number)
        if active_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} כבר קיים במערכת",
                "CLIENT.CONFLICT",
            )

        deleted_clients = self.client_repo.get_deleted_by_id_number(id_number)
        if deleted_clients:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {id_number} קיים במערכת אך נמחק",
                "CLIENT.DELETED_EXISTS",
            )

        try:
            client = self.client_repo.create(
                full_name=full_name, id_number=id_number, id_number_type=id_number_type,
                phone=phone, email=email, address_street=address_street,
                address_building_number=address_building_number, address_apartment=address_apartment,
                address_city=address_city, address_zip_code=address_zip_code,
                created_by=actor_id,
            )
        except IntegrityError:
            raise ConflictError(f"לקוח עם מספר ת.ז. {id_number} כבר קיים", "CLIENT.CONFLICT")

        create_initial_binder(self.db, client, actor_id)
        if actor_id:
            self._audit.append(
                entity_type=ENTITY_CLIENT, entity_id=client.id,
                performed_by=actor_id, action=ACTION_CREATED,
                new_value=json.dumps({"full_name": full_name, "id_number": id_number}),
            )
        return client

    def get_client(self, client_id: int) -> Optional[Client]:
        return self.client_repo.get_by_id(client_id)

    def get_client_or_raise(self, client_id: int) -> Client:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        return client

    def update_client(self, client_id: int, actor_id: Optional[int] = None, **fields) -> Client:
        """Update client identity fields (name, phone, email, address)."""
        existing = self.get_client_or_raise(client_id)
        old_snapshot = {k: getattr(existing, k, None) for k in fields if hasattr(existing, k)}
        updated = self.client_repo.update(client_id, **fields)
        new_snapshot = {k: getattr(updated, k, None) for k in fields if hasattr(updated, k)}
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_UPDATED,
            old_value=json.dumps({k: str(v) if v is not None else None for k, v in old_snapshot.items()}),
            new_value=json.dumps({k: str(v) if v is not None else None for k, v in new_snapshot.items()}),
        )
        return updated

    def delete_client(self, client_id: int, actor_id: int) -> None:
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client or client.deleted_at is not None:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        self.client_repo.soft_delete(client_id, deleted_by=actor_id)
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_DELETED,
        )

    def restore_client(self, client_id: int, actor_id: int) -> Client:
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError("לקוח זה אינו מחוק", "CLIENT.NOT_DELETED")

        active = self.client_repo.get_active_by_id_number(client.id_number)
        if active:
            raise ConflictError(
                f"לקוח עם מספר ת.ז. {client.id_number} כבר קיים ופעיל במערכת",
                "CLIENT.CONFLICT",
            )

        restored = self.client_repo.restore(client_id, restored_by=actor_id)
        if not restored:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
        self._audit.append(
            entity_type=ENTITY_CLIENT, entity_id=client_id,
            performed_by=actor_id, action=ACTION_RESTORED,
        )
        return restored

    # ─── Query delegation ────────────────────────────────────────────────────

    def list_clients(self, search=None, status=None, sort_by="full_name", sort_order="asc", page=1, page_size=20):
        return self._query.list_clients(
            search=search, status=status, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
        )

    def list_all_clients(self):
        return self._query.list_all_clients()

    def get_conflict_info(self, id_number: str) -> dict:
        return self._query.get_conflict_info(id_number)
