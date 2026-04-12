"""Business update logic — extracted to keep BusinessService within 150 lines."""

import json
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.audit.constants import ACTION_UPDATED, ENTITY_BUSINESS
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.models.business import Business, BusinessStatus
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole


def _serialize(d: dict) -> dict:
    return {
        k: v.value if hasattr(v, "value") else str(v) if v is not None else None
        for k, v in d.items()
    }


class BusinessUpdateService:
    def __init__(self, db: Session):
        self._repo = BusinessRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def update_business(
        self,
        business_id: int,
        client_id: int,
        user_role: UserRole,
        actor_id: Optional[int] = None,
        **fields,
    ) -> Business:
        """Update business fields. FROZEN/CLOSED status requires ADVISOR role."""
        business = self._repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        if business.client_id != client_id:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")

        if "status" in fields and fields["status"] is not None:
            try:
                fields["status"] = BusinessStatus(fields["status"])
            except ValueError:
                raise AppError(
                    f"סטטוס לא חוקי: {fields['status']}", "BUSINESS.INVALID_STATUS", status_code=400
                )

        new_status = fields.get("status")
        if new_status in (BusinessStatus.FROZEN, BusinessStatus.CLOSED):
            if user_role != UserRole.ADVISOR:
                raise ForbiddenError("רק יועצים יכולים להקפיא או לסגור עסקים", "BUSINESS.FORBIDDEN")
        if new_status == BusinessStatus.CLOSED:
            fields.setdefault("closed_at", date.today())
        if new_status == BusinessStatus.ACTIVE:
            fields["closed_at"] = None

        fields.pop("entity_type", None)

        old_snapshot = {k: getattr(business, k, None) for k in fields if hasattr(business, k)}
        updated = self._repo.update(business_id, **fields)
        new_snapshot = {k: getattr(updated, k, None) for k in fields if hasattr(updated, k)}

        if actor_id:
            self._audit.append(
                entity_type=ENTITY_BUSINESS,
                entity_id=business_id,
                performed_by=actor_id,
                action=ACTION_UPDATED,
                old_value=json.dumps(_serialize(old_snapshot)),
                new_value=json.dumps(_serialize(new_snapshot)),
            )
        return updated
