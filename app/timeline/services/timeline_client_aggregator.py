from app.clients.models.legal_entity import LegalEntity
from app.clients.models.client_record import ClientRecord
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.permanent_documents.models.permanent_document import PermanentDocument
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository

_TIMELINE_BULK_LIMIT = 500

from app.timeline.services.timeline_client_builders import (
    client_created_event,
    client_info_updated_event,
    document_uploaded_event,
    reminder_created_event,
    signature_request_created_event,
)


def build_client_events(
    db,
    client_record_id: int,
    business_ids: list[int],
    reminder_repo: ReminderRepository,
    sig_repo: SignatureRequestRepository,
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
        if client.updated_at and client.updated_at != client.created_at:
            events.append(client_info_updated_event(client))

    for business_id in business_ids:
        reminders = reminder_repo.list_by_business(
            business_id, page=1, page_size=_TIMELINE_BULK_LIMIT
        )
        for reminder in reminders:
            events.append(reminder_created_event(reminder))

    client_reminders = reminder_repo.list_by_client_record(
        client_record_id, page=1, page_size=_TIMELINE_BULK_LIMIT
    )
    for reminder in client_reminders:
        events.append(reminder_created_event(reminder))

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

    for business_id in business_ids:
        sig_requests = sig_repo.list_by_business(
            business_id, page=1, page_size=_TIMELINE_BULK_LIMIT
        )
        for sig in sig_requests:
            events.append(signature_request_created_event(sig))

    return events
