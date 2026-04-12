from datetime import date, datetime
from types import SimpleNamespace

from app.common.enums import EntityType
from app.permanent_documents.models.permanent_document import DocumentType
from app.reminders.models.reminder import ReminderType
from app.signature_requests.models.signature_request import (
    SignatureRequestStatus,
    SignatureRequestType,
)
from app.timeline.services.timeline_client_builders import (
    client_created_event,
    client_info_updated_event,
    document_uploaded_event,
    reminder_created_event,
    signature_request_created_event,
)


def test_client_builder_events():
    client = SimpleNamespace(
        full_name="Client Builder",
        opened_at=date(2026, 1, 1),
        updated_at=datetime(2026, 1, 2, 8, 0),
        entity_type=EntityType.COMPANY_LTD,
    )

    created = client_created_event(client)
    assert created["event_type"] == "client_created"
    assert created["description"] == "לקוח נוצר: Client Builder"
    assert created["metadata"] == {"entity_type": "company_ltd"}

    updated = client_info_updated_event(client)
    assert updated["event_type"] == "client_info_updated"
    assert updated["timestamp"] == datetime(2026, 1, 2, 8, 0)


def test_reminder_document_and_signature_builder_events():
    reminder = SimpleNamespace(
        reminder_type=ReminderType.CUSTOM,
        created_at=datetime(2026, 1, 4, 10, 0),
        binder_id=3,
        charge_id=4,
        send_on=date(2026, 1, 10),
    )
    document = SimpleNamespace(
        document_type=DocumentType.ID_COPY,
        uploaded_at=datetime(2026, 1, 5, 11, 0),
    )
    signature_request = SimpleNamespace(
        id=15,
        request_type=SignatureRequestType.ANNUAL_REPORT_APPROVAL,
        created_at=datetime(2026, 1, 6, 12, 0),
        status=SignatureRequestStatus.PENDING_SIGNATURE,
    )

    reminder_event = reminder_created_event(reminder)
    assert reminder_event["event_type"] == "reminder_created"
    assert reminder_event["metadata"] == {
        "reminder_type": "custom",
        "send_on": "2026-01-10",
    }

    document_event = document_uploaded_event(document)
    assert document_event["event_type"] == "document_uploaded"
    assert document_event["metadata"] == {"document_type": "id_copy"}

    signature_event = signature_request_created_event(signature_request)
    assert signature_event["event_type"] == "signature_request_created"
    assert signature_event["metadata"] == {
        "signature_request_id": 15,
        "status": "pending_signature",
    }
