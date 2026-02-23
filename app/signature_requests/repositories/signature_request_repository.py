"""
Repository entry point for SignatureRequest and SignatureAuditEvent.

This class composes CRUD and audit mixins to keep this file lean while
preserving the original public API and import path.
"""

from sqlalchemy.orm import Session

from app.signature_requests.repositories.signature_request_audit import SignatureRequestAuditMixin
from app.signature_requests.repositories.signature_request_crud import SignatureRequestCrudMixin


class SignatureRequestRepository(SignatureRequestCrudMixin, SignatureRequestAuditMixin):
    def __init__(self, db: Session):
        self.db = db


__all__ = ["SignatureRequestRepository"]
