from __future__ import annotations

from sqlalchemy.orm import Session

from app.clients.repositories.client_repository import ClientRepository
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.signature_requests.services import admin_actions, create_request, queries, send_request, signer_actions


class SignatureRequestService:
    """
    Orchestrates digital signature request lifecycle.
    Thin façade delegating to smaller feature modules.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = SignatureRequestRepository(db)
        self.client_repo = ClientRepository(db)

    # Create
    def create_request(self, **kwargs):
        return create_request.create_request(self.repo, self.client_repo, **kwargs)

    # Send
    def send_request(self, **kwargs):
        return send_request.send_request(self.repo, **kwargs)

    # Signer actions
    def record_view(self, **kwargs):
        return signer_actions.record_view(self.repo, **kwargs)

    def sign_request(self, **kwargs):
        return signer_actions.sign_request(self.repo, **kwargs)

    def decline_request(self, **kwargs):
        return signer_actions.decline_request(self.repo, **kwargs)

    # Advisor/system actions
    def cancel_request(self, **kwargs):
        return admin_actions.cancel_request(self.repo, **kwargs)

    def expire_overdue_requests(self):
        return admin_actions.expire_overdue_requests(self.repo)

    # Queries
    def get_request(self, request_id: int):
        return queries.get_request(self.repo, request_id)

    def get_by_token(self, token: str):
        return queries.get_by_token(self.repo, token)

    def list_client_requests(self, **kwargs):
        return queries.list_client_requests(self.repo, **kwargs)

    def list_pending_requests(self, **kwargs):
        return queries.list_pending_requests(self.repo, **kwargs)

    def get_audit_trail(self, request_id: int):
        return queries.get_audit_trail(self.repo, request_id)
