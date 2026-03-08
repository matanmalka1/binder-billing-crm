from app.clients.models.client import Client
from app.clients.models.client_tax_profile import ClientTaxProfile
from app.permanent_documents.models.permanent_document import PermanentDocument
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.timeline.services.timeline_client_builders import (
    client_created_event,
    client_info_updated_event,
    document_uploaded_event,
    reminder_created_event,
    signature_request_created_event,
    tax_profile_updated_event,
)

_TIMELINE_BULK_LIMIT = 500


def build_client_events(
    db,
    client_id: int,
    reminder_repo: ReminderRepository,
    sig_repo: SignatureRequestRepository,
) -> list[dict]:
    events = []

    client = db.query(Client).filter(Client.id == client_id).first()
    if client:
        events.append(client_created_event(client))
        if getattr(client, "updated_at", None):
            events.append(client_info_updated_event(client))

    profile = db.query(ClientTaxProfile).filter(
        ClientTaxProfile.client_id == client_id
    ).first()
    if profile and profile.updated_at:
        events.append(tax_profile_updated_event(profile))

    reminders = reminder_repo.list_by_client(
        client_id, page=1, page_size=_TIMELINE_BULK_LIMIT
    )
    for reminder in reminders:
        events.append(reminder_created_event(reminder))

    docs = (
        db.query(PermanentDocument)
        .filter(
            PermanentDocument.client_id == client_id,
            PermanentDocument.is_deleted.is_(False),
        )
        .all()
    )
    for doc in docs:
        events.append(document_uploaded_event(doc))

    sig_requests = sig_repo.list_by_client(
        client_id, page=1, page_size=_TIMELINE_BULK_LIMIT
    )
    for sig in sig_requests:
        events.append(signature_request_created_event(sig))

    return events
