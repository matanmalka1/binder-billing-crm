from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.schemas.client_status_card import ClientStatusCardResponse
from app.clients.services.status_card_service import StatusCardService

router = APIRouter(
    prefix="/businesses",
    tags=["businesses"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{business_id}/status-card", response_model=ClientStatusCardResponse)
def get_business_status_card(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    year: Optional[int] = Query(None, ge=2000, le=2100),
):
    """Comprehensive status card for a business — VAT, annual report, charges, advances, binders, documents."""
    service = StatusCardService(db)
    return service.get_status_card(business_id, year=year)
