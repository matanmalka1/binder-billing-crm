import pytest
from datetime import date

from app.businesses.models.business import Business
from app.core.exceptions import AppError
from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_service import NotificationService
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import IdNumberType
from sqlalchemy.orm import Session


def _make_client(
    db: Session, *, email: str = "client@test.com", phone: str | None = None
) -> int:
    entity = LegalEntity(
        official_name="Test Entity",
        id_number=f"REM-{id(db)}-{email}",
        id_number_type=IdNumberType.INDIVIDUAL,
    )
    db.add(entity)
    db.flush()
    record = ClientRecord(legal_entity_id=entity.id)
    db.add(record)
    db.flush()
    person = Person(
        full_name="Test Client",
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


def test_notify_client_sends_by_client_record_id(test_db, monkeypatch):
    """notify_client stores business_id as delivery context."""
    entity = LegalEntity(
        official_name="Test Entity CB",
        id_number="REM-CB-001",
        id_number_type=IdNumberType.INDIVIDUAL,
    )
    test_db.add(entity)
    test_db.flush()
    record = ClientRecord(legal_entity_id=entity.id)
    test_db.add(record)
    test_db.flush()
    person = Person(
        full_name="Test Client CB",
        id_number=f"PCB-{record.id}",
        id_number_type=IdNumberType.OTHER,
        email="cb@test.com",
    )
    test_db.add(person)
    test_db.flush()
    test_db.add(
        PersonLegalEntityLink(
            person_id=person.id,
            legal_entity_id=entity.id,
            role=PersonLegalEntityRole.OWNER,
        )
    )
    biz = Business(
        legal_entity_id=entity.id,
        business_name="Test Biz CB",
        opened_at=date.today(),
    )
    test_db.add(biz)
    test_db.flush()
    client_record_id = record.id

    svc = NotificationService(test_db)
    monkeypatch.setattr(svc.email, "_enabled", False)

    ok = svc.notify_client(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
        template_data={"binder_number": "BN-99"},
        business_id=biz.id,
        binder_id=7,
    )

    assert ok is True
    items, total = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert total == 1
    n = items[0]
    assert n.client_record_id == client_record_id
    assert n.business_id == biz.id
    assert n.binder_id == 7
    assert n.channel == NotificationChannel.EMAIL


def test_notify_client_business_id_is_optional_context(test_db, monkeypatch):
    """business_id absent → notification still created, client_record_id is the anchor."""
    client_record_id = _make_client(test_db, email="no-biz@test.com")
    svc = NotificationService(test_db)
    monkeypatch.setattr(svc.email, "_enabled", False)

    ok = svc.notify_client(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        template_data={"binder_number": "BN-1", "period_start": "2026-01"},
    )

    assert ok is True
    items, _ = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert items[0].business_id is None


def test_notify_client_whatsapp_fails_falls_back_to_email(test_db, monkeypatch):
    client_record_id = _make_client(test_db, email="fb@test.com", phone="0501234567")
    svc = NotificationService(test_db)

    monkeypatch.setattr(svc.whatsapp, "_api_key", "fake-key")
    monkeypatch.setattr(svc.whatsapp, "_from_number", "+9720000000")
    monkeypatch.setattr(svc.whatsapp, "send", lambda to, msg: (False, "wa-error"))
    email_calls = []
    monkeypatch.setattr(
        svc.email,
        "send",
        lambda to, msg, subject="": email_calls.append(to) or (True, None),
    )

    ok = svc.notify_client(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
        template_data={"binder_number": "BN-1"},
        preferred_channel=NotificationChannel.WHATSAPP,
    )

    assert ok is True
    assert email_calls == ["fb@test.com"]
    items, total = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert total == 2
    statuses = {n.channel: n.status for n in items}
    assert statuses[NotificationChannel.WHATSAPP] == NotificationStatus.FAILED
    assert statuses[NotificationChannel.EMAIL] == NotificationStatus.SENT


def test_notify_client_missing_template_key_raises_app_error(test_db, monkeypatch):
    client_record_id = _make_client(test_db, email="tmpl@test.com")
    svc = NotificationService(test_db)
    monkeypatch.setattr(svc.email, "_enabled", False)

    with pytest.raises(AppError):
        svc.notify_client(
            client_record_id=client_record_id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            template_data={},  # missing binder_number and period_start
        )

    _, total = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert total == 0
