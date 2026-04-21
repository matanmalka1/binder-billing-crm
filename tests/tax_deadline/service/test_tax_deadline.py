from datetime import date, timedelta

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.reminders.models.reminder import Reminder
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from tests.tax_deadline.factories import create_business


def test_create_update_complete_get_delete_flow(test_db):
    business = create_business(test_db, name_prefix="Service CRUD")
    service = TaxDeadlineService(test_db)

    created = service.create_deadline(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
        payment_amount=5000.00,
        description="February VAT",
    )
    assert created.client_record_id == business.client_id
    assert created.status == TaxDeadlineStatus.PENDING

    reminder = test_db.query(Reminder).filter(Reminder.tax_deadline_id == created.id).first()
    assert reminder is not None

    updated = service.update_deadline(created.id, description="Updated desc", payment_amount=1200)
    assert updated.description == "Updated desc"
    assert float(updated.payment_amount) == 1200

    completed = service.mark_completed(created.id)
    assert completed.status == TaxDeadlineStatus.COMPLETED
    assert completed.completed_at is not None
    completed_at_first = completed.completed_at

    completed_again = service.mark_completed(created.id)
    assert completed_again.id == created.id
    assert completed_again.completed_at == completed_at_first

    fetched = service.get_deadline(created.id)
    assert fetched.id == created.id

    service.delete_deadline(created.id, deleted_by=42)
    with pytest.raises(NotFoundError):
        service.get_deadline(created.id)


def test_create_allows_closed_or_frozen_business(test_db):
    closed = create_business(test_db, name_prefix="Closed Biz")
    frozen = create_business(test_db, name_prefix="Frozen Biz")
    service = TaxDeadlineService(test_db)

    closed_deadline = service.create_deadline(
        closed.client_id, DeadlineType.VAT, date.today() + timedelta(days=2)
    )
    frozen_deadline = service.create_deadline(
        frozen.client_id, DeadlineType.VAT, date.today() + timedelta(days=2)
    )
    assert closed_deadline.client_record_id == closed.client_id
    assert frozen_deadline.client_record_id == frozen.client_id


def test_service_not_found_and_validation_paths(test_db):
    service = TaxDeadlineService(test_db)

    with pytest.raises(AppError):
        service.update_deadline(1)

    with pytest.raises(NotFoundError):
        service.update_deadline(999999, description="x")

    with pytest.raises(NotFoundError):
        service.mark_completed(999999)

    with pytest.raises(NotFoundError):
        service.delete_deadline(999999, deleted_by=1)


def test_list_all_pending_and_get_business_deadlines(test_db):
    business_a = create_business(test_db, name_prefix="Service A")
    business_b = create_business(test_db, name_prefix="Service B")
    service = TaxDeadlineService(test_db)

    a_vat = service.create_deadline(business_a.client_id, DeadlineType.VAT, date.today() + timedelta(days=1))
    a_adv = service.create_deadline(business_a.client_id, DeadlineType.ADVANCE_PAYMENT, date.today() + timedelta(days=2))
    b_vat = service.create_deadline(business_b.client_id, DeadlineType.VAT, date.today() + timedelta(days=3))
    service.mark_completed(a_adv.id)

    pending = service.list_all_pending()
    assert {d.id for d in pending} == {a_vat.id, b_vat.id}

    all_for_a = service.get_client_deadlines(business_a.client_id)
    assert {d.id for d in all_for_a} == {a_vat.id, a_adv.id}

    completed_for_a = service.get_client_deadlines(
        business_a.client_id,
        status=TaxDeadlineStatus.COMPLETED.value,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
    )
    assert [d.id for d in completed_for_a] == [a_adv.id]
