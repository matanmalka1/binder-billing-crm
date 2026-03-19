from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.users.models.user import UserRole
from app.signature_requests.schemas.signature_request import SignatureRequestListResponse, SignatureRequestResponse
from app.signature_requests.services import SignatureRequestService
from app.users.api.deps import CurrentUser, DBSession, require_role

client_router = APIRouter(
    prefix="/businesses",
    tags=["signature-requests"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@client_router.get(
    "/{business_id}/signature-requests",
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
    service = SignatureRequestService(db)
    items, total = service.list_business_requests(
        business_id=business_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    return SignatureRequestListResponse(
        items=[SignatureRequestResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )
