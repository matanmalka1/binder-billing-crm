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
from app.notification.models.notification import NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_send_service import NotificationSendService


def _make_client_with_person(db: Session, *, email: str = "owner@test.com") -> int:
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
    # Disable email so delivery never runs
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
