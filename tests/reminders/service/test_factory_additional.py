from datetime import date, timedelta

import pytest

from app.binders.models.binder import Binder, BinderStatus
from app.businesses.models.business import BusinessStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import AppError, NotFoundError
from app.reminders.services.factory import (
    create_custom_reminder,
    create_idle_binder_reminder,
    create_tax_deadline_reminder,
    create_unpaid_charge_reminder,
)
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.models.tax_deadline import DeadlineType
from tests.helpers.identity import SeededClient, seed_business, seed_client_identity


def _client(db) -> SeededClient:
    return seed_client_identity(
        db,
        full_name="Reminder Factory Client",
        id_number="RMF001",
    )


def _business(db, crm_client: SeededClient):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Reminder Factory Biz {crm_client.id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def test_factory_create_paths_and_default_messages(test_db, test_user):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client)
    reminder_repo = ReminderRepository(test_db)
    business_repo = BusinessRepository(test_db)

    tax_deadline = TaxDeadlineRepository(test_db).create(
        client_record_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )
    tax = create_tax_deadline_reminder(
        reminder_repo,
        ClientRecordRepository(test_db),
        TaxDeadlineRepository(test_db),
        client_record_id=crm_client.id,
        tax_deadline_id=tax_deadline.id,
        target_date=tax_deadline.due_date,
        days_before=3,
        created_by=test_user.id,
    )
    assert tax.send_on == tax_deadline.due_date - timedelta(days=3)

    binder = Binder(
        client_record_id=crm_client.id,
        binder_number="BF-1",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    idle = create_idle_binder_reminder(
        reminder_repo,
        BinderRepository(test_db),
        binder_id=binder.id,
        days_idle=5,
        created_by=test_user.id,
    )
    assert "5" in idle.message

    charge = Charge(
        client_record_id=crm_client.id,
        business_id=business.id,
        amount=10,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
    )
    test_db.add(charge)
    test_db.commit()
    test_db.refresh(charge)

    unpaid = create_unpaid_charge_reminder(
        reminder_repo,
        business_repo,
        ChargeRepository(test_db),
        client_record_id=crm_client.id,
        business_id=business.id,
        charge_id=charge.id,
        days_unpaid=7,
        created_by=test_user.id,
    )
    assert "7" in unpaid.message

    custom = create_custom_reminder(
        reminder_repo,
        business_repo,
        business_id=business.id,
        target_date=date.today() + timedelta(days=2),
        days_before=1,
        message="  custom note  ",
        created_by=test_user.id,
    )
    assert custom.message == "custom note"


def test_factory_validation_errors(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client)
    reminder_repo = ReminderRepository(test_db)
    business_repo = BusinessRepository(test_db)

    with pytest.raises(AppError):
        create_custom_reminder(
            reminder_repo,
            business_repo,
            business_id=business.id,
            target_date=date.today(),
            days_before=-1,
            message="x",
        )

    with pytest.raises(AppError):
        create_custom_reminder(
            reminder_repo,
            business_repo,
            business_id=business.id,
            target_date=date.today(),
            days_before=0,
            message="   ",
        )

    with pytest.raises(NotFoundError):
        create_idle_binder_reminder(
            reminder_repo,
            BinderRepository(test_db),
            binder_id=999999,
            days_idle=1,
        )


def test_tax_deadline_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    tax_repo = TaxDeadlineRepository(test_db)

    with pytest.raises(NotFoundError):
        create_tax_deadline_reminder(
            reminder_repo,
            ClientRecordRepository(test_db),
            tax_repo,
            client_record_id=crm_client.id,
            tax_deadline_id=999999,
            target_date=date.today() + timedelta(days=3),
            days_before=1,
        )

    existing = tax_repo.create(
        client_record_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )
    with pytest.raises(AppError) as exc_info:
        create_tax_deadline_reminder(
            reminder_repo,
            ClientRecordRepository(test_db),
            tax_repo,
            client_record_id=crm_client.id,
            tax_deadline_id=existing.id,
            target_date=existing.due_date,
            days_before=-1,
        )
    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_idle_binder_factory_rejects_negative_days(test_db, test_user):
    crm_client = _client(test_db)
    _business(test_db, crm_client)
    reminder_repo = ReminderRepository(test_db)

    binder = Binder(
        client_record_id=crm_client.id,
        binder_number="BF-NEG",
        period_start=date.today(),
        status=BinderStatus.IN_OFFICE,
        created_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    with pytest.raises(AppError) as exc_info:
        create_idle_binder_reminder(
            reminder_repo,
            BinderRepository(test_db),
            binder_id=binder.id,
            days_idle=-1,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_unpaid_charge_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    business = _business(test_db, crm_client)
    reminder_repo = ReminderRepository(test_db)
    business_repo = BusinessRepository(test_db)
    charge_repo = ChargeRepository(test_db)

    with pytest.raises(NotFoundError):
        create_unpaid_charge_reminder(
            reminder_repo,
            business_repo,
            charge_repo,
            client_record_id=crm_client.id,
            business_id=business.id,
            charge_id=999999,
            days_unpaid=1,
        )

    charge = Charge(
        client_record_id=crm_client.id,
        business_id=business.id,
        amount=55,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
    )
    test_db.add(charge)
    test_db.commit()
    test_db.refresh(charge)

    with pytest.raises(AppError) as exc_info:
        create_unpaid_charge_reminder(
            reminder_repo,
            business_repo,
            charge_repo,
            client_record_id=crm_client.id,
            business_id=business.id,
            charge_id=charge.id,
            days_unpaid=-2,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"
