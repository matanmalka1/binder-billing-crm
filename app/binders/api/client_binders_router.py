from fastapi import APIRouter, Depends, Query

from app.users.api.deps import DBSession, require_role
from app.users.models.user import UserRole
from app.binders.schemas.binder_extended import BinderDetailResponse, BinderListResponseExtended
from app.binders.services.binder_operations_service import BinderOperationsService
from app.clients.services.client_service import ClientService

router = APIRouter(
    prefix="/clients",
    tags=["clients-binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/binders", response_model=BinderListResponseExtended)
def list_client_binders(
    client_id: int,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all binders for a specific client."""
    ClientService(db).get_client_or_raise(client_id)

    service = BinderOperationsService(db)
    items, total = service.get_client_binders(
        client_id=client_id,
        page=page,
        page_size=page_size,
    )

    enriched = [
        BinderDetailResponse(**service.enrich_binder(b))
        for b in items
    ]

    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )
