from sqlalchemy.orm import Session

from app.audit.constants import ACTION_DELETED, ACTION_RESTORED, ENTITY_CLIENT
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_record_read_repository import (
    get_full_record,
    get_full_record_including_deleted,
)
from app.clients.services.messages import (
    CLIENT_ID_NUMBER_ACTIVE_EXISTS,
    CLIENT_NOT_DELETED,
    CLIENT_NOT_FOUND,
)
from app.core.exceptions import ConflictError, NotFoundError


class ClientLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.record_repo = ClientRecordRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def delete_client(self, client_id: int, actor_id: int) -> None:
        client = self.record_repo.get_by_id_including_deleted(client_id)
        if not client or client.deleted_at is not None:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self.record_repo.soft_delete(client_id, deleted_by=actor_id)
        self._audit.append(entity_type=ENTITY_CLIENT, entity_id=client_id, performed_by=actor_id, action=ACTION_DELETED)

    def restore_client(self, client_id: int, actor_id: int):
        client = self.record_repo.get_by_id_including_deleted(client_id)
        if not client:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        if client.deleted_at is None:
            raise ConflictError(CLIENT_NOT_DELETED, "CLIENT.NOT_DELETED")
        full_client = get_full_record_including_deleted(self.db, client_id)
        id_number = full_client.get("id_number") if full_client else None
        if id_number and self.record_repo.get_active_by_id_number(id_number):
            raise ConflictError(
                CLIENT_ID_NUMBER_ACTIVE_EXISTS.format(id_number=id_number),
                "CLIENT.CONFLICT",
            )
        restored_record = self.record_repo.restore(client_id, restored_by=actor_id)
        restored = get_full_record(self.db, restored_record.id) if restored_record else None
        if not restored:
            raise NotFoundError(CLIENT_NOT_FOUND.format(client_id=client_id), "CLIENT.NOT_FOUND")
        self._audit.append(
            entity_type=ENTITY_CLIENT,
            entity_id=client_id,
            performed_by=actor_id,
            action=ACTION_RESTORED,
        )
        return restored
