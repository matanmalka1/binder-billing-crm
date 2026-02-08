from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
from app.repositories import ClientRepository
from app.schemas.binder_extended import (
    BinderDetailResponse,
    BinderListResponseExtended,
)
from app.services.binder_operations_service import BinderOperationsService

router = APIRouter(
    prefix="/clients",
    tags=["clients-binders"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@router.get("/{client_id}/binders", response_model=BinderListResponseExtended)
def list_client_binders(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all binders for a specific client."""
    # Verify client exists
    client_repo = ClientRepository(db)
    client = client_repo.get_by_id(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    service = BinderOperationsService(db)
    items, total = service.get_client_binders(
        client_id=client_id,
        page=page,
        page_size=page_size,
    )
    
    enriched = [
        BinderDetailResponse(**service.enrich_binder_with_sla(b))
        for b in items
    ]
    
    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )
