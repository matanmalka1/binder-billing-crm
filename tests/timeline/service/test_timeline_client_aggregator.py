from datetime import date, datetime

from app.clients.models import Client, ClientType
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.permanent_documents.models.permanent_document import DocumentType, PermanentDocument
from app.reminders.models.reminder import ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.signature_requests.models.signature_request import SignatureRequestType
from app.signature_requests.repositories.signature_request_repository import (
    SignatureRequestRepository,
)
from app.timeline.services.timeline_client_aggregator import build_client_events
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Timeline Aggregator User",
        email="timeline.aggregator@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db) -> Client:
    client = Client(
        full_name="Timeline Aggregator Client",
        id_number="TAC001",
        client_type=ClientType.COMPANY,
        opened_at=date(2026, 1, 1),
        updated_at=datetime(2026, 1, 2, 8, 0),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_build_client_events_collects_all_client_side_sources(test_db):
    user = _user(test_db)
    client = _client(test_db)

    profile = ClientTaxProfile(
        client_id=client.id,
        vat_type=VatType.MONTHLY,
        updated_at=datetime(2026, 1, 3, 9, 0),
    )
    test_db.add(profile)

    reminder_repo = ReminderRepository(test_db)
    reminder_repo.create(
        client_id=client.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=date(2026, 1, 20),
        days_before=2,
        send_on=date(2026, 1, 18),
        message="Reminder",
    )

    test_db.add(
        PermanentDocument(
            client_id=client.id,
            document_type=DocumentType.ID_COPY,
            storage_key="clients/1/id_copy/file.pdf",
            uploaded_by=user.id,
            uploaded_at=datetime(2026, 1, 4, 10, 0),
            is_deleted=False,
        )
    )
    test_db.commit()

    sig_repo = SignatureRequestRepository(test_db)
    sig_repo.create(
        client_id=client.id,
        created_by=user.id,
        request_type=SignatureRequestType.CUSTOM,
        title="Signature",
        signer_name="Signer",
    )

    events = build_client_events(test_db, client.id, reminder_repo, sig_repo)
    event_types = {event["event_type"] for event in events}

    assert event_types == {
        "client_created",
        "client_info_updated",
        "tax_profile_updated",
        "reminder_created",
        "document_uploaded",
        "signature_request_created",
    }

