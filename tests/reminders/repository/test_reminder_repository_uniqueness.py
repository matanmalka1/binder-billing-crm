from datetime import date, timedelta
from itertools import count

import pytest
from sqlalchemy.exc import IntegrityError

from app.businesses.models.business import BusinessStatus
from app.reminders.models.reminder import ReminderStatus, ReminderType
from app.reminders.repositories.reminder_repository import ReminderRepository
from tests.helpers.identity import SeededClient, seed_business, seed_client_identity


_seq = count(1)


def _client(db) -> SeededClient:
    idx = next(_seq)
    return seed_client_identity(
        db,
        full_name=f"Reminder Unique Client {idx}",
        id_number=f"RMU{idx:03d}",
    )


def _business(db, crm_client: SeededClient):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name=f"Reminder Unique Biz {crm_client.id}",
        status=BusinessStatus.ACTIVE,
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def test_active_reminder_identity_is_unique(test_db):
    repo = ReminderRepository(test_db)
    crm_client = _client(test_db)
    business = _business(test_db, crm_client)
    target = date.today() + timedelta(days=7)

    repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target,
        days_before=2,
        send_on=target - timedelta(days=2),
        message="first",
    )

    with pytest.raises(IntegrityError):
        repo.create(
            client_record_id=crm_client.id,
            business_id=business.id,
            reminder_type=ReminderType.CUSTOM,
            target_date=target,
            days_before=1,
            send_on=target - timedelta(days=1),
            message="duplicate",
        )


def test_canceled_reminder_identity_can_be_recreated(test_db):
    repo = ReminderRepository(test_db)
    crm_client = _client(test_db)
    business = _business(test_db, crm_client)
    target = date.today() + timedelta(days=7)

    canceled = repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target,
        days_before=2,
        send_on=target - timedelta(days=2),
        message="old",
    )
    repo.update_status(canceled.id, ReminderStatus.CANCELED)

    recreated = repo.create(
        client_record_id=crm_client.id,
        business_id=business.id,
        reminder_type=ReminderType.CUSTOM,
        target_date=target,
        days_before=1,
        send_on=target - timedelta(days=1),
        message="new",
    )

    assert recreated.id != canceled.id
