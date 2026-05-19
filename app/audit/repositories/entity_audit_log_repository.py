"""Repository for EntityAuditLog entities."""


from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models.entity_audit_log import EntityAuditLog
from app.common.repositories.base_repository import BaseRepository


class EntityAuditLogRepository(BaseRepository[EntityAuditLog]):
    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        entity_type: str,
        entity_id: int,
        performed_by: int,
        action: str,
        old_value: str | None = None,
        new_value: str | None = None,
        note: str | None = None,
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
        limit: int = 50,
        offset: int = 0,
    ) -> list[EntityAuditLog]:
        return self.db.scalars(
            select(EntityAuditLog)
            .where(
                EntityAuditLog.entity_type == entity_type,
                EntityAuditLog.entity_id == entity_id,
            )
            .order_by(EntityAuditLog.performed_at.desc(), EntityAuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()

    def count_audit_trail(self, entity_type: str, entity_id: int) -> int:
        return self.db.scalar(
            select(func.count(EntityAuditLog.id)).where(
                EntityAuditLog.entity_type == entity_type,
                EntityAuditLog.entity_id == entity_id,
            )
        )

    def list_recent(self, limit: int = 5) -> list[EntityAuditLog]:
        return self.db.scalars(
            select(EntityAuditLog)
            .order_by(EntityAuditLog.performed_at.desc(), EntityAuditLog.id.desc())
            .limit(limit)
        ).all()
