from datetime import date, timedelta

import pytest

from app.businesses.models.business import BusinessStatus
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.reminders.models.reminder import Reminder
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from tests.tax_deadline.factories import create_business


def test_create_update_complete_get_delete_flow(test_db):
    business = create_business(test_db, name_prefix="Service CRUD")
    service = TaxDeadlineService(test_db)

    created = service.create_deadline(
        business_id=business.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
        payment_amount=5000.00,
        description="February VAT",
    )
    assert created.business_id == business.id
    assert created.status == TaxDeadlineStatus.PENDING

    reminder = test_db.query(Reminder).filter(Reminder.tax_deadline_id == created.id).first()
    assert reminder is not None

    updated = service.update_deadline(created.id, description="Updated desc", payment_amount=1200)
    assert updated.description == "Updated desc"
    assert float(updated.payment_amount) == 1200

    completed = service.mark_completed(created.id)
    assert completed.status == TaxDeadlineStatus.COMPLETED
    assert completed.completed_at is not None

    fetched = service.get_deadline(created.id)
    assert fetched.id == created.id

    service.delete_deadline(created.id, deleted_by=42)
    with pytest.raises(NotFoundError):
        service.get_deadline(created.id)


def test_create_rejects_closed_or_frozen_business(test_db):
    closed = create_business(test_db, name_prefix="Closed Biz", status=BusinessStatus.CLOSED)
    frozen = create_business(test_db, name_prefix="Frozen Biz", status=BusinessStatus.FROZEN)
    service = TaxDeadlineService(test_db)

    with pytest.raises(ForbiddenError):
        service.create_deadline(closed.id, DeadlineType.VAT, date.today() + timedelta(days=2))

    with pytest.raises(ForbiddenError):
        service.create_deadline(frozen.id, DeadlineType.VAT, date.today() + timedelta(days=2))


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

    a_vat = service.create_deadline(business_a.id, DeadlineType.VAT, date.today() + timedelta(days=1))
    a_adv = service.create_deadline(business_a.id, DeadlineType.ADVANCE_PAYMENT, date.today() + timedelta(days=2))
    b_vat = service.create_deadline(business_b.id, DeadlineType.VAT, date.today() + timedelta(days=3))
    service.mark_completed(a_adv.id)

    pending = service.list_all_pending()
    assert {d.id for d in pending} == {a_vat.id, b_vat.id}

    all_for_a = service.get_business_deadlines(business_a.id)
    assert {d.id for d in all_for_a} == {a_vat.id, a_adv.id}

    completed_for_a = service.get_business_deadlines(
        business_a.id,
        status=TaxDeadlineStatus.COMPLETED.value,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
    )
    assert [d.id for d in completed_for_a] == [a_adv.id]
