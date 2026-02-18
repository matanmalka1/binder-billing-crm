from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users.models.user import UserRole
from app.signature_requests.schemas.signature_request import (
    CancelRequest,
    SignatureAuditEventResponse,
    SignatureRequestCreateRequest,
    SignatureRequestListResponse,
    SignatureRequestResponse,
    SignatureRequestSendRequest,
    SignatureRequestSentResponse,
    SignatureRequestWithAuditResponse,
)
from app.signature_requests.services import SignatureRequestService
from app.users.api.deps import CurrentUser, DBSession, require_role

advisor_router = APIRouter(
    prefix="/signature-requests",
    tags=["signature-requests"],
    dependencies=[Depends(require_role(UserRole.ADVISOR, UserRole.SECRETARY))],
)


@advisor_router.post("", response_model=SignatureRequestResponse, status_code=status.HTTP_201_CREATED)
def create_signature_request(
    request: SignatureRequestCreateRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = SignatureRequestService(db)
    try:
        req = service.create_request(
            client_id=request.client_id,
            created_by=user.id,
            created_by_name=user.full_name,
            request_type=request.request_type,
            title=request.title,
            description=request.description,
            signer_name=request.signer_name,
            signer_email=request.signer_email,
            signer_phone=request.signer_phone,
            annual_report_id=request.annual_report_id,
            document_id=request.document_id,
            content_to_hash=request.content_to_hash,
        )
        return SignatureRequestResponse.model_validate(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@advisor_router.get("/pending", response_model=SignatureRequestListResponse)
def list_pending_requests(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = SignatureRequestService(db)
    items, total = service.list_pending_requests(page=page, page_size=page_size)
    return SignatureRequestListResponse(
        items=[SignatureRequestResponse.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@advisor_router.get("/{request_id}", response_model=SignatureRequestWithAuditResponse)
def get_signature_request(request_id: int, db: DBSession, user: CurrentUser):
    service = SignatureRequestService(db)
    req = service.get_request(request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature request not found")

    audit_events = service.get_audit_trail(request_id)
    response = SignatureRequestWithAuditResponse.model_validate(req)
    response.audit_trail = [SignatureAuditEventResponse.model_validate(e) for e in audit_events]
    return response


@advisor_router.post("/{request_id}/send", response_model=SignatureRequestSentResponse)
def send_signature_request(
    request_id: int,
    body: SignatureRequestSendRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = SignatureRequestService(db)
    try:
        req = service.send_request(
            request_id=request_id,
            sent_by=user.id,
            sent_by_name=user.full_name,
            expiry_days=body.expiry_days,
        )
        response = SignatureRequestSentResponse.model_validate(req)
        response.signing_token = req.signing_token
        response.signing_url_hint = f"/sign/{req.signing_token}"
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@advisor_router.post("/{request_id}/cancel", response_model=SignatureRequestResponse)
def cancel_signature_request(
    request_id: int,
    body: CancelRequest,
    db: DBSession,
    user: CurrentUser,
):
    service = SignatureRequestService(db)
    try:
        req = service.cancel_request(
            request_id=request_id,
            canceled_by=user.id,
            canceled_by_name=user.full_name,
            reason=body.reason,
        )
        return SignatureRequestResponse.model_validate(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@advisor_router.get("/{request_id}/audit-trail", response_model=list[SignatureAuditEventResponse])
def get_audit_trail(request_id: int, db: DBSession, user: CurrentUser):
    service = SignatureRequestService(db)
    req = service.get_request(request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature request not found")
    events = service.get_audit_trail(request_id)
    return [SignatureAuditEventResponse.model_validate(e) for e in events]
