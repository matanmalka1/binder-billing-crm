from app.clients.models.client_record import ClientRecord
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.permanent_documents.models.permanent_document import PermanentDocument
from app.signature_requests.models.signature_request import SignatureAuditEvent, SignatureRequest
from app.timeline.services.timeline_client_builders import (
    client_created_event,
    document_uploaded_event,
    signature_request_lifecycle_event,
)

_TIMELINE_BULK_LIMIT = 500


def build_client_events(
    db,
    client_record_id: int,
    business_ids: list[int],
) -> list[dict]:
    events = []

    client_record = (
        db.query(ClientRecord)
        .filter(ClientRecord.id == client_record_id, ClientRecord.deleted_at.is_(None))
        .first()
    )
    client = (
        LegalEntityRepository(db).get_by_id(client_record.legal_entity_id)
        if client_record
        else None
    )
    if client:
        events.append(client_created_event(client))

    docs = []
    if business_ids:
        docs = (
            db.query(PermanentDocument)
            .filter(
                PermanentDocument.business_id.in_(business_ids),
                PermanentDocument.is_deleted.is_(False),
            )
            .limit(_TIMELINE_BULK_LIMIT)
            .all()
        )
    for doc in docs:
        events.append(document_uploaded_event(doc))

    lifecycle_types = ("sent", "signed", "declined", "canceled", "expired")
    signature_rows = (
        db.query(SignatureRequest, SignatureAuditEvent)
        .join(
            SignatureAuditEvent,
            SignatureAuditEvent.signature_request_id == SignatureRequest.id,
        )
        .filter(
            SignatureRequest.client_record_id == client_record_id,
            SignatureRequest.deleted_at.is_(None),
            SignatureAuditEvent.event_type.in_(lifecycle_types),
        )
        .order_by(SignatureAuditEvent.occurred_at.desc())
        .limit(_TIMELINE_BULK_LIMIT)
        .all()
    )
    for sig, audit_event in signature_rows:
        events.append(signature_request_lifecycle_event(sig, audit_event))

    return events
