from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.signature_requests.models.signature_request import (
    SignatureRequestStatus,
    SignatureRequestType,
)


# ── Audit event ───────────────────────────────────────────────────────────────

class SignatureAuditEventResponse(BaseModel):
    id: int
    event_type: str     # String במודל — לא enum, מרחיב בחופשיות
    actor_type: str     # String במודל — לא enum
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    ip_address: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


# ── Core response ─────────────────────────────────────────────────────────────

class SignatureRequestResponse(BaseModel):
    id: int
    business_id: int
    created_by: int
    request_type: SignatureRequestType      # enum
    title: str
    description: Optional[str] = None
    signer_name: str
    signer_email: Optional[str] = None
    signer_phone: Optional[str] = None
    status: SignatureRequestStatus          # enum
    content_hash: Optional[str] = None
    storage_key: Optional[str] = None
    annual_report_id: Optional[int] = None
    document_id: Optional[int] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    canceled_by: Optional[int] = None      # קיים במודל, חסר בגרסה הישנה
    signer_ip_address: Optional[str] = None
    decline_reason: Optional[str] = None
    signed_document_key: Optional[str] = None

    model_config = {"from_attributes": True}


class SignatureRequestListResponse(BaseModel):
    items: list[SignatureRequestResponse]
    page: int
    page_size: int
    total: int


class SignatureRequestWithAuditResponse(SignatureRequestResponse):
    audit_trail: list[SignatureAuditEventResponse] = []


# ── Advisor requests ──────────────────────────────────────────────────────────

class SignatureRequestCreateRequest(BaseModel):
    business_id: int = Field(gt=0)
    request_type: SignatureRequestType      # enum
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    signer_name: str = Field(min_length=2, max_length=100)
    signer_email: Optional[EmailStr] = None
    signer_phone: Optional[str] = None
    annual_report_id: Optional[int] = Field(None, gt=0)
    document_id: Optional[int] = Field(None, gt=0)
    content_to_hash: Optional[str] = None  # service יחשב SHA-256


class SignatureRequestSendRequest(BaseModel):
    expiry_days: int = Field(14, ge=1, le=90)


class SignatureRequestSentResponse(SignatureRequestResponse):
    """מוחזר פעם אחת בלבד — token לא נשמר בצד שרת."""
    signing_token: Optional[str] = None
    signing_url_hint: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# ── Signer-facing (public, ללא JWT) ──────────────────────────────────────────

class SignerViewResponse(BaseModel):
    """מינימלי — ללא מזהים פנימיים או נתונים פיננסיים."""
    request_id: int
    title: str
    description: Optional[str] = None
    signer_name: str
    status: SignatureRequestStatus          # enum
    content_hash: Optional[str] = None
    expires_at: Optional[datetime] = None


class SignerDeclineRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)