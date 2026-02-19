"""
Pydantic schemas for the Digital Signature workflow.

Advisor-facing schemas are authenticated and use standard request/response
patterns consistent with the rest of the CRM.

Signer-facing schemas are used on the public signing endpoint (token-based,
no JWT) and intentionally expose minimal information.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------ #
# Audit event                                                          #
# ------------------------------------------------------------------ #


class SignatureAuditEventResponse(BaseModel):
    id: int
    event_type: str
    actor_type: str
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    ip_address: Optional[str] = None
    notes: Optional[str] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Signature request — core response                                    #
# ------------------------------------------------------------------ #


class SignatureRequestResponse(BaseModel):
    id: int
    client_id: int
    created_by: int
    request_type: str
    title: str
    description: Optional[str] = None
    signer_name: str
    signer_email: Optional[str] = None
    signer_phone: Optional[str] = None
    status: str
    content_hash: Optional[str] = None
    storage_key: Optional[str] = None
    annual_report_id: Optional[int] = None
    document_id: Optional[int] = None

    # Timestamps
    created_at: datetime
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Outcome evidence (available after signing/declining)
    signer_ip_address: Optional[str] = None
    decline_reason: Optional[str] = None
    signed_document_key: Optional[str] = None

    # signing_token is intentionally excluded from this response; it is only
    # returned once at send-time via SignatureRequestSentResponse.

    model_config = {"from_attributes": True}


class SignatureRequestListResponse(BaseModel):
    items: list[SignatureRequestResponse]
    page: int
    page_size: int
    total: int


class SignatureRequestWithAuditResponse(SignatureRequestResponse):
    """Extended response that includes the full audit trail."""
    audit_trail: list[SignatureAuditEventResponse] = []


# ------------------------------------------------------------------ #
# Advisor-facing request bodies                                       #
# ------------------------------------------------------------------ #


class SignatureRequestCreateRequest(BaseModel):
    client_id: int = Field(..., gt=0)
    request_type: str = Field(
        ...,
        description=(
            "One of: engagement_agreement, annual_report_approval, "
            "power_of_attorney, vat_return_approval, custom"
        ),
    )
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    signer_name: str = Field(..., min_length=2, max_length=100)
    signer_email: Optional[str] = None
    signer_phone: Optional[str] = None

    # Optional links
    annual_report_id: Optional[int] = Field(None, gt=0)
    document_id: Optional[int] = Field(None, gt=0)

    # If the advisor wants content-level tamper detection, pass the
    # canonical text of what is being signed.
    content_to_hash: Optional[str] = None


class SignatureRequestSendRequest(BaseModel):
    expiry_days: int = Field(14, ge=1, le=90, description="Days until the signing link expires")


class SignatureRequestSentResponse(SignatureRequestResponse):
    """
    Returned to the advisor after calling /send.

    Includes the signing_token ONCE so the advisor's system can
    construct the signing URL to share with the client.
    The token is not stored in plain-text after this point.
    """
    signing_token: Optional[str] = None
    signing_url_hint: Optional[str] = None  # e.g. "https://crm.example.com/sign/{token}"


class CancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


# ------------------------------------------------------------------ #
# Signer-facing schemas (public endpoints, no JWT)                   #
# ------------------------------------------------------------------ #


class SignerViewResponse(BaseModel):
    """
    What the signer sees when they open the signing URL.

    Intentionally minimal — no internal IDs, no financial data.
    """
    request_id: int
    title: str
    description: Optional[str] = None
    signer_name: str
    status: str
    content_hash: Optional[str] = None  # Signer can independently verify
    expires_at: Optional[datetime] = None


class SignerDeclineRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
