from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import UserRole
from app.signature_requests.schemas.signature_request import (
    SignatureRequestListResponse,
    SignatureRequestResponse,
)
from app.signature_requests.services.signature_request_service import SignatureRequestService
from app.users.api.deps import CurrentUser, DBSession, require_role

client_router = APIRouter(
    tags=["signature-requests"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@client_router.get(
    "/clients/{client_id}/signature-requests",
    response_model=SignatureRequestListResponse,
)
def list_client_signature_requests(
    client_id: int,
    db: DBSession,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """All signature requests for a legal entity, across all businesses."""
    service = SignatureRequestService(db)
    items, total = service.list_client_requests(
        client_id=client_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    client_repo = ClientRepository(db)
    office_number_map = {
        client.id: client.office_client_number
        for client in client_repo.list_by_ids(sorted({item.client_id for item in items}))
    }
    return SignatureRequestListResponse(
        items=[
            SignatureRequestResponse.model_validate(r).model_copy(
                update={"office_client_number": office_number_map.get(r.client_id)}
            )
            for r in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@client_router.get(
    "/businesses/{business_id}/signature-requests",
    response_model=SignatureRequestListResponse,
)
def list_business_signature_requests(
    business_id: int,
    db: DBSession,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Signature requests scoped to a specific business (filtered view)."""
    service = SignatureRequestService(db)
    items, total = service.list_business_requests(
        business_id=business_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    client_repo = ClientRepository(db)
    office_number_map = {
        client.id: client.office_client_number
        for client in client_repo.list_by_ids(sorted({item.client_id for item in items}))
    }
    return SignatureRequestListResponse(
        items=[
            SignatureRequestResponse.model_validate(r).model_copy(
                update={"office_client_number": office_number_map.get(r.client_id)}
            )
            for r in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
