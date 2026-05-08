"""Routes: read-only audit trail queries."""

from fastapi import APIRouter, Depends, Query

from app.audit.schemas.entity_audit_log import EntityAuditTrailResponse
from app.audit.services.audit_trail_service import AuditTrailService
from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=EntityAuditTrailResponse,
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)
def get_entity_audit_trail(
    entity_type: str,
    entity_id: int,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Get the full audit trail for any audited entity."""
    return AuditTrailService(db).get_entity_audit_trail(entity_type, entity_id, limit, offset)
