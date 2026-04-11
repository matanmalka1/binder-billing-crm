from app.businesses.models.business import Business
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
    client_id: int,
    business_ids: list[int],
    reminder_repo: ReminderRepository,
    sig_repo: SignatureRequestRepository,
) -> list[dict]:
    events = []

    client_businesses = (
        db.query(Business)
        .filter(
            Business.client_id == client_id,
            Business.deleted_at.is_(None),
        )
        .order_by(Business.opened_at.asc(), Business.id.asc())
        .all()
    )
    if client_businesses:
        primary_business = client_businesses[0]
        events.append(client_created_event(primary_business))
        if primary_business.updated_at and primary_business.updated_at != primary_business.created_at:
            events.append(client_info_updated_event(primary_business))

    for business_id in business_ids:
        reminders = reminder_repo.list_by_business(
            business_id, page=1, page_size=_TIMELINE_BULK_LIMIT
        )
        for reminder in reminders:
            events.append(reminder_created_event(reminder))

    client_reminders = reminder_repo.list_by_client(
        client_id, page=1, page_size=_TIMELINE_BULK_LIMIT
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
