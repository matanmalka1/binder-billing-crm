from datetime import date, timedelta

import pytest

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType
from app.core.exceptions import AppError, NotFoundError
from app.reminders.services.factory import (
    create_custom_reminder,
    create_idle_binder_reminder,
    create_tax_deadline_reminder,
    create_unpaid_charge_reminder,
)
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.clients.repositories.client_repository import ClientRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.models.tax_deadline import DeadlineType


def _client(db) -> Client:
    crm_client = Client(
        full_name="Reminder Factory Client",
        id_number="RMF001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_factory_create_paths_and_default_messages(test_db, test_user):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    client_repo = ClientRepository(test_db)

    tax_deadline = TaxDeadlineRepository(test_db).create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )
    tax = create_tax_deadline_reminder(
        reminder_repo,
        client_repo,
        TaxDeadlineRepository(test_db),
        client_id=crm_client.id,
        tax_deadline_id=tax_deadline.id,
        target_date=tax_deadline.due_date,
        days_before=3,
        created_by=test_user.id,
    )
    assert tax.send_on == tax_deadline.due_date - timedelta(days=3)

    binder = Binder(
        client_id=crm_client.id,
        binder_number="BF-1",
        binder_type=BinderType.OTHER,
        received_at=date.today(),
        received_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    idle = create_idle_binder_reminder(
        reminder_repo,
        client_repo,
        BinderRepository(test_db),
        client_id=crm_client.id,
        binder_id=binder.id,
        days_idle=5,
        created_by=test_user.id,
    )
    assert "5" in idle.message

    charge = Charge(
        client_id=crm_client.id,
        amount=10,
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
    )
    test_db.add(charge)
    test_db.commit()
    test_db.refresh(charge)

    unpaid = create_unpaid_charge_reminder(
        reminder_repo,
        client_repo,
        ChargeRepository(test_db),
        client_id=crm_client.id,
        charge_id=charge.id,
        days_unpaid=7,
        created_by=test_user.id,
    )
    assert "7" in unpaid.message

    custom = create_custom_reminder(
        reminder_repo,
        client_repo,
        client_id=crm_client.id,
        target_date=date.today() + timedelta(days=2),
        days_before=1,
        message="  custom note  ",
        created_by=test_user.id,
    )
    assert custom.message == "custom note"


def test_factory_validation_errors(test_db):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    client_repo = ClientRepository(test_db)

    with pytest.raises(AppError):
        create_custom_reminder(
            reminder_repo,
            client_repo,
            client_id=crm_client.id,
            target_date=date.today(),
            days_before=-1,
            message="x",
        )

    with pytest.raises(AppError):
        create_custom_reminder(
            reminder_repo,
            client_repo,
            client_id=crm_client.id,
            target_date=date.today(),
            days_before=0,
            message="   ",
        )

    with pytest.raises(NotFoundError):
        create_idle_binder_reminder(
            reminder_repo,
            client_repo,
            BinderRepository(test_db),
            client_id=crm_client.id,
            binder_id=999999,
            days_idle=1,
        )


def test_tax_deadline_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    client_repo = ClientRepository(test_db)
    tax_repo = TaxDeadlineRepository(test_db)

    with pytest.raises(NotFoundError):
        create_tax_deadline_reminder(
            reminder_repo,
            client_repo,
            tax_repo,
            client_id=crm_client.id,
            tax_deadline_id=999999,
            target_date=date.today() + timedelta(days=3),
            days_before=1,
        )

    existing = tax_repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )
    with pytest.raises(AppError) as exc_info:
        create_tax_deadline_reminder(
            reminder_repo,
            client_repo,
            tax_repo,
            client_id=crm_client.id,
            tax_deadline_id=existing.id,
            target_date=existing.due_date,
            days_before=-1,
        )
    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_idle_binder_factory_rejects_negative_days(test_db, test_user):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    client_repo = ClientRepository(test_db)

    binder = Binder(
        client_id=crm_client.id,
        binder_number="BF-NEG",
        binder_type=BinderType.OTHER,
        received_at=date.today(),
        received_by=test_user.id,
        status=BinderStatus.IN_OFFICE,
    )
    test_db.add(binder)
    test_db.commit()
    test_db.refresh(binder)

    with pytest.raises(AppError) as exc_info:
        create_idle_binder_reminder(
            reminder_repo,
            client_repo,
            BinderRepository(test_db),
            client_id=crm_client.id,
            binder_id=binder.id,
            days_idle=-1,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"


def test_unpaid_charge_factory_not_found_and_negative_days(test_db):
    crm_client = _client(test_db)
    reminder_repo = ReminderRepository(test_db)
    client_repo = ClientRepository(test_db)
    charge_repo = ChargeRepository(test_db)

    with pytest.raises(NotFoundError):
        create_unpaid_charge_reminder(
            reminder_repo,
            client_repo,
            charge_repo,
            client_id=crm_client.id,
            charge_id=999999,
            days_unpaid=1,
        )

    charge = Charge(
        client_id=crm_client.id,
        amount=55,
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
    )
    test_db.add(charge)
    test_db.commit()
    test_db.refresh(charge)

    with pytest.raises(AppError) as exc_info:
        create_unpaid_charge_reminder(
            reminder_repo,
            client_repo,
            charge_repo,
            client_id=crm_client.id,
            charge_id=charge.id,
            days_unpaid=-2,
        )

    assert exc_info.value.code == "REMINDER.NEGATIVE_DAYS"
