from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.signature_requests.schemas.signature_request import SignerDeclineRequest, SignerViewResponse
from app.signature_requests.services import SignatureRequestService
from app.users.api.deps import DBSession

signer_router = APIRouter(
    prefix="/sign",
    tags=["signature-signing"],
)


@signer_router.get("/{token}", response_model=SignerViewResponse)
def signer_view(token: str, raw_request: Request, db: DBSession):
    service = SignatureRequestService(db)
    try:
        req = service.record_view(
            token=token,
            ip_address=raw_request.client.host if raw_request.client else None,
            user_agent=raw_request.headers.get("user-agent"),
        )
        return SignerViewResponse(
            request_id=req.id,
            title=req.title,
            description=req.description,
            signer_name=req.signer_name,
            status=req.status.value,
            content_hash=req.content_hash,
            expires_at=req.expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@signer_router.post("/{token}/approve", response_model=SignerViewResponse)
def signer_approve(token: str, raw_request: Request, db: DBSession):
    service = SignatureRequestService(db)
    try:
        req = service.sign_request(
            token=token,
            ip_address=raw_request.client.host if raw_request.client else None,
            user_agent=raw_request.headers.get("user-agent"),
        )
        return SignerViewResponse(
            request_id=req.id,
            title=req.title,
            description=req.description,
            signer_name=req.signer_name,
            status=req.status.value,
            content_hash=req.content_hash,
            expires_at=req.expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@signer_router.post("/{token}/decline", response_model=SignerViewResponse)
def signer_decline(token: str, body: SignerDeclineRequest, raw_request: Request, db: DBSession):
    service = SignatureRequestService(db)
    try:
        req = service.decline_request(
            token=token,
            reason=body.reason,
            ip_address=raw_request.client.host if raw_request.client else None,
            user_agent=raw_request.headers.get("user-agent"),
        )
        return SignerViewResponse(
            request_id=req.id,
            title=req.title,
            description=req.description,
            signer_name=req.signer_name,
            status=req.status.value,
            content_hash=req.content_hash,
            expires_at=req.expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
