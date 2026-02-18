from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.users.models.user import UserRole
from app.signature_requests.schemas.signature_request import SignatureRequestListResponse, SignatureRequestResponse
from app.signature_requests.services import SignatureRequestService
from app.users.api.deps import CurrentUser, DBSession, require_role

client_router = APIRouter(
    prefix="/clients",
    tags=["signature-requests"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@client_router.get(
    "/{client_id}/signature-requests",
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
    service = SignatureRequestService(db)
    try:
        items, total = service.list_client_requests(
            client_id=client_id,
            status=status_filter,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SignatureRequestListResponse(
        items=[SignatureRequestResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )
