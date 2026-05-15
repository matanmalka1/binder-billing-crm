"""Integration tests for NotificationSendService — delivery engine."""

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import IdNumberType
from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_send_service import NotificationSendService


def _make_client_with_person(
    db: Session,
    *,
    email: str = "owner@test.com",
    phone: str | None = None,
) -> int:
    entity = LegalEntity(
        official_name="Test Entity",
        id_number=f"SS-{id(db)}",
        id_number_type=IdNumberType.INDIVIDUAL,
    )
    db.add(entity)
    db.flush()

    record = ClientRecord(legal_entity_id=entity.id)
    db.add(record)
    db.flush()

    person = Person(
        full_name="Test Owner",
        id_number=f"P-{record.id}",
        id_number_type=IdNumberType.OTHER,
        email=email,
        phone=phone,
    )
    db.add(person)
    db.flush()

    db.add(
        PersonLegalEntityLink(
            person_id=person.id,
            legal_entity_id=entity.id,
            role=PersonLegalEntityRole.OWNER,
        )
    )
    db.flush()
    return record.id


def test_send_client_notification_missing_template_key_returns_false_without_persisting(
    test_db, monkeypatch
):
    client_record_id = _make_client_with_person(test_db)
    svc = NotificationSendService(test_db)
    monkeypatch.setattr(svc.email, "_enabled", False)

    ok = svc.send_client_notification(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        template_data={},  # missing binder_number and period_start
    )

    assert ok is False
    _, total = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert total == 0


def test_send_client_notification_whatsapp_fails_falls_back_to_email(
    test_db, monkeypatch
):
    client_record_id = _make_client_with_person(
        test_db, email="fallback@test.com", phone="0501234567"
    )
    svc = NotificationSendService(test_db)

    monkeypatch.setattr(svc.whatsapp, "_api_key", "fake-key")
    monkeypatch.setattr(svc.whatsapp, "_from_number", "+9720000000")
    monkeypatch.setattr(svc.whatsapp, "send", lambda to, msg: (False, "wa-error"))
    email_calls = []
    monkeypatch.setattr(
        svc.email,
        "send",
        lambda to, msg, subject="": email_calls.append(to) or (True, None),
    )

    ok = svc.send_client_notification(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
        template_data={"binder_number": "BN-1"},
        preferred_channel=NotificationChannel.WHATSAPP,
    )

    assert ok is True
    assert email_calls == ["fallback@test.com"]

    repo = NotificationRepository(test_db)
    items, total = repo.list_paginated(client_record_id=client_record_id)
    assert total == 2
    statuses = {n.channel: n.status for n in items}
    assert statuses[NotificationChannel.WHATSAPP] == NotificationStatus.FAILED
    assert statuses[NotificationChannel.EMAIL] == NotificationStatus.SENT
