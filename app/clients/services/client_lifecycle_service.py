from sqlalchemy.orm import Session

from app.audit.constants import ACTION_DELETED, ACTION_RESTORED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.clients.repositories.client_repository import ClientRepository
from app.clients.services.messages import (
    CLIENT_ID_NUMBER_ACTIVE_EXISTS,
    CLIENT_NOT_DELETED,
    CLIENT_NOT_FOUND,
)
from app.core.exceptions import ConflictError, NotFoundError


class ClientLifecycleService:
    def __init__(self, db: Session):
        self.client_repo = ClientRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def delete_client(self, client_id: int, actor_id: int) -> None:
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client or client.deleted_at is not None:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self.client_repo.soft_delete(client_id, deleted_by=actor_id)
        self._audit.append(entity_type=ENTITY_CLIENT, entity_id=client_id, performed_by=actor_id, action=ACTION_DELETED)

    def restore_client(self, client_id: int, actor_id: int):
        client = self.client_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError(CLIENT_NOT_DELETED, "CLIENT.NOT_DELETED")
        if self.client_repo.get_active_by_id_number(client.id_number):
            raise ConflictError(
                CLIENT_ID_NUMBER_ACTIVE_EXISTS.format(id_number=client.id_number),
                "CLIENT.CONFLICT",
            )
        restored = self.client_repo.restore(client_id, restored_by=actor_id)
        if not restored:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self._audit.append(
            entity_type=ENTITY_CLIENT,
            entity_id=client_id,
            performed_by=actor_id,
            action=ACTION_RESTORED,
        )
        return restored
