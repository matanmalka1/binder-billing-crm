from fastapi import APIRouter, Depends, HTTPException, status

from app.users.api.deps import CurrentUser, DBSession, require_role
from app.users.models.user import UserRole
from app.clients.schemas.client_status_card import ClientStatusCardResponse
from app.clients.services.status_card_service import StatusCardService

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/status-card", response_model=ClientStatusCardResponse)
def get_client_status_card(client_id: int, db: DBSession, user: CurrentUser):
    """Comprehensive status card for a client — VAT, annual report, charges, advances, binders, documents."""
    service = StatusCardService(db)
    try:
        return service.get_status_card(client_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
