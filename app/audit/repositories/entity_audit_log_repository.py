"""Repository for EntityAuditLog entities."""

from typing import Optional

from sqlalchemy.orm import Session

from app.audit.models.entity_audit_log import EntityAuditLog


class EntityAuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        entity_type: str,
        entity_id: int,
        performed_by: int,
        action: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        note: Optional[str] = None,
    ) -> EntityAuditLog:
        entry = EntityAuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            performed_by=performed_by,
            action=action,
            old_value=old_value,
            new_value=new_value,
            note=note,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_audit_trail(
        self,
        entity_type: str,
        entity_id: int,
    ) -> list[EntityAuditLog]:
        return (
            self.db.query(EntityAuditLog)
            .filter(
                EntityAuditLog.entity_type == entity_type,
                EntityAuditLog.entity_id == entity_id,
            )
            .order_by(EntityAuditLog.performed_at.asc())
            .all()
        )
