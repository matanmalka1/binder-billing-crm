from datetime import date, timedelta
from itertools import count
from types import SimpleNamespace

import pytest

from app.businesses.models.business import Business, BusinessStatus, EntityType
from app.clients.models.client import Client
from app.core.exceptions import AppError, NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.reminders.models.reminder import ReminderType
from app.reminders.services.reminder_service import ReminderService
from app.reminders.services.factory_extended import (
    create_advance_payment_due_reminder,
    create_annual_report_deadline_reminder,
    create_document_missing_reminder,
    create_vat_filing_reminder,
)


_client_seq = count(1)


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder Extended Factory Client",
        id_number=f"RMX{next(_client_seq):06d}",
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def _business(db, client_id: int) -> Business:
    business = Business(
        client_id=client_id,
        entity_type=EntityType.COMPANY_LTD,
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


class _ReminderRepoMock:
    def create(self, **kwargs):
        return SimpleNamespace(**kwargs)


def test_vat_filing_factory_default_message_and_send_on(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    target_date = date.today() + timedelta(days=9)

    reminder = create_vat_filing_reminder(
        _ReminderRepoMock(),
        BusinessRepository(test_db),
        SimpleNamespace(get_by_id=lambda _id: object()),
        business_id=business.id,
        tax_deadline_id=111,
        target_date=target_date,
        days_before=3,
    )

    assert reminder.reminder_type == ReminderType.VAT_FILING
    assert reminder.send_on == target_date - timedelta(days=3)
    assert "3" in reminder.message


def test_vat_filing_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    reminder_repo = _ReminderRepoMock()
    business_repo = BusinessRepository(test_db)

    with pytest.raises(NotFoundError):
        create_vat_filing_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: None),
            business_id=business.id,
            tax_deadline_id=999,
            target_date=date.today() + timedelta(days=4),
            days_before=1,
        )

    with pytest.raises(AppError) as exc_info:
        create_vat_filing_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: object()),
            business_id=business.id,
            tax_deadline_id=1,
            target_date=date.today() + timedelta(days=4),
            days_before=-1,
        )
    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_annual_report_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    reminder_repo = _ReminderRepoMock()
    business_repo = BusinessRepository(test_db)

    with pytest.raises(NotFoundError):
        create_annual_report_deadline_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: None),
            business_id=business.id,
            annual_report_id=999,
            target_date=date.today() + timedelta(days=4),
            days_before=1,
        )

    with pytest.raises(AppError) as exc_info:
        create_annual_report_deadline_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: object()),
            business_id=business.id,
            annual_report_id=1,
            target_date=date.today() + timedelta(days=4),
            days_before=-1,
        )
    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_annual_report_factory_default_message_and_send_on(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    target_date = date.today() + timedelta(days=11)

    reminder = create_annual_report_deadline_reminder(
        _ReminderRepoMock(),
        BusinessRepository(test_db),
        SimpleNamespace(get_by_id=lambda _id: object()),
        business_id=business.id,
        annual_report_id=5,
        target_date=target_date,
        days_before=4,
    )

    assert reminder.reminder_type == ReminderType.ANNUAL_REPORT_DEADLINE
    assert reminder.send_on == target_date - timedelta(days=4)
    assert "4" in reminder.message


def test_advance_payment_factory_default_message_and_send_on(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    target_date = date.today() + timedelta(days=14)

    reminder = create_advance_payment_due_reminder(
        _ReminderRepoMock(),
        BusinessRepository(test_db),
        SimpleNamespace(get_by_id=lambda _id: object()),
        business_id=business.id,
        advance_payment_id=444,
        target_date=target_date,
        days_before=2,
    )

    assert reminder.reminder_type == ReminderType.ADVANCE_PAYMENT_DUE
    assert reminder.send_on == target_date - timedelta(days=2)
    assert "2" in reminder.message


def test_advance_payment_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    reminder_repo = _ReminderRepoMock()
    business_repo = BusinessRepository(test_db)

    with pytest.raises(NotFoundError):
        create_advance_payment_due_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: None),
            business_id=business.id,
            advance_payment_id=999,
            target_date=date.today() + timedelta(days=3),
            days_before=1,
        )

    with pytest.raises(AppError) as exc_info:
        create_advance_payment_due_reminder(
            reminder_repo,
            business_repo,
            SimpleNamespace(get_by_id=lambda _id: object()),
            business_id=business.id,
            advance_payment_id=1,
            target_date=date.today() + timedelta(days=3),
            days_before=-1,
        )
    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_document_missing_factory_validation_and_trimming(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client.id)
    reminder_repo = _ReminderRepoMock()
    business_repo = BusinessRepository(test_db)

    with pytest.raises(AppError):
        create_document_missing_reminder(
            reminder_repo,
            business_repo,
            business_id=business.id,
            target_date=date.today(),
            days_before=-1,
            message="x",
        )

    with pytest.raises(AppError):
        create_document_missing_reminder(
            reminder_repo,
            business_repo,
            business_id=business.id,
            target_date=date.today(),
            days_before=0,
            message="   ",
        )

    reminder = create_document_missing_reminder(
        reminder_repo,
        business_repo,
        business_id=business.id,
        target_date=date.today() + timedelta(days=1),
        days_before=1,
        message="  מסמך חסר  ",
    )
    assert reminder.reminder_type == ReminderType.DOCUMENT_MISSING
    assert reminder.message == "מסמך חסר"


def test_reminder_service_delegates_extended_creation_methods(monkeypatch, test_db):
    service = ReminderService(test_db)
    monkeypatch.setattr("app.reminders.services.factory_extended.create_vat_filing_reminder", lambda *_a, **_k: "vat")
    monkeypatch.setattr(
        "app.reminders.services.factory_extended.create_annual_report_deadline_reminder",
        lambda *_a, **_k: "annual",
    )
    monkeypatch.setattr(
        "app.reminders.services.factory_extended.create_advance_payment_due_reminder",
        lambda *_a, **_k: "advance",
    )
    monkeypatch.setattr(
        "app.reminders.services.factory_extended.create_document_missing_reminder",
        lambda *_a, **_k: "document",
    )

    assert service.create_vat_filing_reminder() == "vat"
    assert service.create_annual_report_deadline_reminder() == "annual"
    assert service.create_advance_payment_due_reminder() == "advance"
    assert service.create_document_missing_reminder() == "document"
