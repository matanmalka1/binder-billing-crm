from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.businesses.schemas.business_status_card import ClientStatusCardResponse
from app.businesses.services.status_card_service import StatusCardService
from app.clients.constants import (
    CLIENT_STATUS_CARD_YEAR_MAX,
    CLIENT_STATUS_CARD_YEAR_MIN,
)

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/status-card", response_model=ClientStatusCardResponse)
def get_client_status_card(
    client_id: int,
    db: DBSession,
    year: Optional[int] = Query(None, ge=CLIENT_STATUS_CARD_YEAR_MIN, le=CLIENT_STATUS_CARD_YEAR_MAX),
):
    """Comprehensive status card for a client — VAT, annual report, charges, advances, binders, documents."""
    return StatusCardService(db).get_status_card(client_id, year=year)
