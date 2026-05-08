"""Write abstraction for generic business entity audit events."""

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.audit.constants import (
    ACTION_CREATED,
    ACTION_DELETED,
    ACTION_RESTORED,
    ACTION_STATUS_CHANGED,
    ACTION_UPDATED,
)
from app.audit.models.entity_audit_log import EntityAuditLog
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository


class EntityAuditWriter:
    def __init__(self, db: Session):
        self._repo = EntityAuditLogRepository(db)

    def append(
        self,
        entity_type: str,
        entity_id: int,
        actor_id: Optional[int],
        action: str,
        old_value: Any = None,
        new_value: Any = None,
        note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        if actor_id is None:
            return None
        return self._repo.append(
            entity_type=entity_type,
            entity_id=entity_id,
            performed_by=actor_id,
            action=action,
            old_value=self._serialize_value(old_value),
            new_value=self._serialize_value(new_value),
            note=note,
        )

    def record_create(
        self, entity_type: str, entity_id: int, actor_id: Optional[int],
        new_value: Any = None, note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        return self.append(entity_type, entity_id, actor_id, ACTION_CREATED, new_value=new_value, note=note)

    def record_update(
        self, entity_type: str, entity_id: int, actor_id: Optional[int],
        old_value: Any = None, new_value: Any = None, note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        return self.append(entity_type, entity_id, actor_id, ACTION_UPDATED, old_value, new_value, note)

    def record_delete(
        self, entity_type: str, entity_id: int, actor_id: Optional[int],
        old_value: Any = None, note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        return self.append(entity_type, entity_id, actor_id, ACTION_DELETED, old_value=old_value, note=note)

    def record_restore(
        self, entity_type: str, entity_id: int, actor_id: Optional[int],
        new_value: Any = None, note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        return self.append(entity_type, entity_id, actor_id, ACTION_RESTORED, new_value=new_value, note=note)

    def record_status_change(
        self, entity_type: str, entity_id: int, actor_id: Optional[int],
        old_status: Any, new_status: Any, note: Optional[str] = None,
    ) -> Optional[EntityAuditLog]:
        return self.append(
            entity_type, entity_id, actor_id, ACTION_STATUS_CHANGED,
            old_value={"status": self._status_value(old_status)},
            new_value={"status": self._status_value(new_status)},
            note=note,
        )

    def _serialize_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            value = {"value": value}
        return json.dumps(value, default=str, ensure_ascii=False)

    def _status_value(self, status: Any) -> Any:
        return status.value if hasattr(status, "value") else status
