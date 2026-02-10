from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession, require_role
from app.models import UserRole
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
    service = BinderOperationsService(db)

    if not service.client_exists(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    items, total = service.get_client_binders(
        client_id=client_id,
        page=page,
        page_size=page_size,
    )
    
    enriched = [
        BinderDetailResponse(**service.enrich_binder_with_sla(b, db))
        for b in items
    ]
    
    return BinderListResponseExtended(
        items=enriched,
        page=page,
        page_size=page_size,
        total=total,
    )
