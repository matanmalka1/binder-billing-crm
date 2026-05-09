from datetime import date, timedelta

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueSourceType,
    WorkQueueUrgency,
)
from app.work_queue.services.work_queue_service import WorkQueueService
from tests.helpers.task_helpers import create_business
from tests.helpers.tax_calendar_links import create_linked_advance_payment


def test_unpaid_charge_item_after_threshold(test_db):
    biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=500,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today() - timedelta(days=31),
    )
    test_db.add(charge)
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)
    unpaid = [i for i in items if i.source_type == WorkQueueSourceType.UNPAID_CHARGE]

    assert len(unpaid) == 1
    assert unpaid[0].source_id == charge.id
    assert unpaid[0].urgency == WorkQueueUrgency.OVERDUE


def test_unpaid_charge_before_threshold_excluded(test_db):
    biz = create_business(test_db)
    test_db.add(
        Charge(
            client_record_id=biz.client_id,
            business_id=biz.id,
            amount=200,
            charge_type=ChargeType.OTHER,
            status=ChargeStatus.ISSUED,
            issued_at=date.today() - timedelta(days=10),
        )
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)

    assert [i for i in items if i.source_type == WorkQueueSourceType.UNPAID_CHARGE] == []


def test_work_queue_excludes_reminders(test_db):
    biz = create_business(test_db)
    today = date.today()
    test_db.add(
        Reminder(
            client_record_id=biz.client_id,
            reminder_type=ReminderType.CUSTOM,
            status=ReminderStatus.PENDING,
            target_date=today + timedelta(days=2),
            days_before=0,
            send_on=today,
            message="תזכורת בדיקה",
        )
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)

    assert items == []


def test_work_queue_advance_payment_includes_source_payload(test_db):
    biz = create_business(test_db)
    due_date = date.today() - timedelta(days=1)
    payment = create_linked_advance_payment(
        test_db,
        client_record_id=biz.client_id,
        period="2026-02",
        due_date=due_date,
        expected_amount=1000,
        paid_amount=250,
    )
    payment.status = AdvancePaymentStatus.PARTIAL
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)
    item = next(i for i in items if i.source_type == WorkQueueSourceType.ADVANCE_PAYMENT)

    assert item.payload == {
        "period": "2026-02",
        "period_months_count": 1,
        "due_date": due_date.isoformat(),
        "status": "partial",
        "expected_amount": "1000.00",
        "paid_amount": "250.00",
        "remaining_amount": "750.00",
        "payment_method": None,
        "paid_at": None,
        "annual_report_id": None,
    }


def test_work_queue_excludes_requested_source_types(test_db, monkeypatch):
    service = WorkQueueService(test_db)
    excluded_builder = lambda *args: (_ for _ in ()).throw(
        AssertionError("excluded builder called")
    )
    monkeypatch.setattr(
        "app.work_queue.services.work_queue_service.vat_filing_items",
        excluded_builder,
    )
    monkeypatch.setattr(
        "app.work_queue.services.work_queue_service.annual_report_items",
        excluded_builder,
    )
    monkeypatch.setattr(
        "app.work_queue.services.work_queue_service.advance_payment_items",
        excluded_builder,
    )
    monkeypatch.setattr(
        "app.work_queue.services.work_queue_service.unpaid_charge_items",
        excluded_builder,
    )

    items = service.list_items(exclude_source_types=list(WorkQueueSourceType))

    assert items == []


def test_work_queue_item_can_be_unscoped_to_client():
    item = WorkQueueItem(
        source_type=WorkQueueSourceType.VAT_FILING,
        source_id=1,
        label='מע"מ לא הוגש: 2026-04',
        due_date=date.today(),
        urgency=WorkQueueUrgency.APPROACHING,
    )

    assert item.client_record_id is None
