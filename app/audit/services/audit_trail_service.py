"""Service layer for read-only entity audit trail queries."""

from sqlalchemy.orm import Session

from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.audit.schemas.entity_audit_log import EntityAuditLogResponse, EntityAuditTrailResponse
from app.users.repositories.user_repository import UserRepository


class AuditTrailService:
    def __init__(self, db: Session):
        self.audit_repo = EntityAuditLogRepository(db)
        self.user_repo = UserRepository(db)

    def get_entity_audit_trail(
        self,
        entity_type: str,
        entity_id: int,
    ) -> EntityAuditTrailResponse:
        entries = self.audit_repo.get_audit_trail(entity_type, entity_id)
        user_ids = list({entry.performed_by for entry in entries})
        users = self.user_repo.list_by_ids(user_ids) if user_ids else []
        user_map = {user.id: user.full_name for user in users}

        items = []
        for entry in entries:
            row = EntityAuditLogResponse.model_validate(entry)
            row.performed_by_name = user_map.get(entry.performed_by)
            items.append(row)
        return EntityAuditTrailResponse(items=items)
