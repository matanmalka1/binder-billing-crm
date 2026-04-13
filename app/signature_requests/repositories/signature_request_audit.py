from typing import Optional

from sqlalchemy.orm import Session

from app.signature_requests.models.signature_request import SignatureAuditEvent
from app.utils.time_utils import utcnow


class SignatureRequestAuditMixin:
    db: Session

    def append_audit_event(
        self,
        signature_request_id: int,
        event_type: str,
        actor_type: str,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SignatureAuditEvent:
        event = SignatureAuditEvent(
            signature_request_id=signature_request_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_name=actor_name,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
            occurred_at=utcnow(),
        )
        self.db.add(event)
        self.db.flush()
        return event

    def list_audit_events(self, signature_request_id: int) -> list[SignatureAuditEvent]:
        return (
            self.db.query(SignatureAuditEvent)
            .filter(SignatureAuditEvent.signature_request_id == signature_request_id)
            .order_by(SignatureAuditEvent.occurred_at.asc())
            .all()
        )
