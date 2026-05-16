from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

from app.businesses.models.business import Business
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import IdNumberType
from app.core.exceptions import AppError
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_service import NotificationService
from datetime import date


def _make_client(db, *, email: str = "owner@test.com", phone: str | None = None) -> int:
    entity = LegalEntity(
        official_name="Test Entity",
        id_number=f"SVC-{id(db)}-{email}",
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


def _make_client_with_business(db, *, email: str = "biz@test.com") -> tuple[int, int]:
    """Returns (client_record_id, business_id)."""
    entity = LegalEntity(
        official_name="Biz Entity",
        id_number=f"BIZ-{id(db)}-{email}",
        id_number_type=IdNumberType.INDIVIDUAL,
    )
    db.add(entity)
    db.flush()
    record = ClientRecord(legal_entity_id=entity.id)
    db.add(record)
    db.flush()
    person = Person(
        full_name="Biz Owner",
        id_number=f"BP-{record.id}",
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
    biz = Business(
        legal_entity_id=entity.id,
        business_name="Test Biz",
        opened_at=date.today(),
    )
    db.add(biz)
    db.flush()
    return record.id, biz.id


def test_list_paginated_enriches_names(test_db):
    service = NotificationService(test_db)
    n1 = SimpleNamespace(
        id=1,
        client_record_id=8,
        business_id=4,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="a@x.com",
        content_snapshot="x",
        severity=NotificationSeverity.INFO,
        status=NotificationStatus.PENDING,
        sent_at=None,
        failed_at=None,
        error_message=None,
        retry_count=0,
        triggered_by=None,
        created_at=datetime.now(UTC),
    )
    service.notification_repo = SimpleNamespace(
        list_paginated=lambda **kwargs: ([n1], 1),
    )
    service.business_repo = SimpleNamespace(
        list_by_ids=lambda ids: [SimpleNamespace(id=4, full_name="Biz 4")],
    )

    items, total = service.list_paginated(page=2, page_size=10, business_id=4)
    assert total == 1
    assert items[0].business_name == "Biz 4"


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


def test_notify_client_rejects_mismatched_business_id(test_db, monkeypatch):
    client_record_id_a, _ = _make_client_with_business(test_db, email="a@test.com")
    _, biz_b_id = _make_client_with_business(test_db, email="b@test.com")

    svc = NotificationService(test_db)
    monkeypatch.setattr(svc.email, "_enabled", False)

    with pytest.raises(AppError) as exc_info:
        svc.notify_client(
            client_record_id=client_record_id_a,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            template_data={"binder_number": "BN-1", "period_start": "2026-01"},
            business_id=biz_b_id,
        )
    assert exc_info.value.code == "NOTIFICATION.BUSINESS_MISMATCH"


def test_get_summary_returns_correct_counts(test_db):
    client_record_id = _make_client(test_db, email="sum@test.com")
    repo = NotificationRepository(test_db)

    n_sent = repo.create(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="sum@test.com",
        content_snapshot="sent",
    )
    repo.mark_sent(n_sent.id)

    n_failed = repo.create(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="sum@test.com",
        content_snapshot="failed",
    )
    repo.mark_failed(n_failed.id, "err")

    repo.create(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="sum@test.com",
        content_snapshot="pending",
    )

    svc = NotificationService(test_db)
    summary = svc.get_summary(client_record_id=client_record_id)
    assert summary.sent == 1
    assert summary.failed == 1
    assert summary.pending == 1
    assert summary.total == 3


def test_get_summary_returns_zeros_for_absent_statuses(test_db):
    client_record_id = _make_client(test_db, email="zero@test.com")
    repo = NotificationRepository(test_db)
    n = repo.create(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient="zero@test.com",
        content_snapshot="sent-only",
    )
    repo.mark_sent(n.id)

    svc = NotificationService(test_db)
    summary = svc.get_summary(client_record_id=client_record_id)
    assert summary.pending == 0
    assert summary.failed == 0
    assert summary.sent == 1
    assert summary.total == 1


def test_notify_client_email_failure_persists_failed_record(test_db, monkeypatch):
    client_record_id = _make_client(test_db, email="fail@test.com")
    svc = NotificationService(test_db)

    monkeypatch.setattr(
        svc.email,
        "send",
        lambda to, msg, subject="": (False, "smtp-err"),
    )

    ok = svc.notify_client(
        client_record_id=client_record_id,
        trigger=NotificationTrigger.BINDER_RECEIVED,
        template_data={"binder_number": "BN-1", "period_start": "2026-01"},
    )

    assert ok is False
    items, total = NotificationRepository(test_db).list_paginated(
        client_record_id=client_record_id
    )
    assert total == 1
    assert items[0].status == NotificationStatus.FAILED
