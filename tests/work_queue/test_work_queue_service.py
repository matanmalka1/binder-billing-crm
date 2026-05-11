from datetime import date, timedelta

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models.client_record import ClientRecord
from app.reminders.models.reminder import Reminder, ReminderActionType, ReminderStatus
from app.utils.time_utils import utcnow
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

    assert [
        i for i in items if i.source_type == WorkQueueSourceType.UNPAID_CHARGE
    ] == []


def test_work_queue_excludes_reminders(test_db):
    biz = create_business(test_db)
    test_db.add(
        Reminder(
            fire_at=utcnow(),
            action_type=ReminderActionType.SEND_NOTIFICATION,
            status=ReminderStatus.SCHEDULED,
            source_domain="client_record",
            source_id=biz.client_id,
        )
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)

    assert items == []


def test_work_queue_advance_payment_includes_source_payload(test_db):
    biz = create_business(test_db)
    client_record = test_db.get(ClientRecord, biz.client_id)
    client_record.office_client_number = 1
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
    item = next(
        i for i in items if i.source_type == WorkQueueSourceType.ADVANCE_PAYMENT
    )

    assert item.client_name.startswith("Task Test Client")
    assert item.client_office_number == 1
    assert item.payload == {
        "period": "2026-02",
        "period_label": "פברואר 2026",
        "period_months_count": 1,
        "frequency": "monthly",
        "due_date": due_date.isoformat(),
        "status": "partial",
        "expected_amount": "1000.00",
        "paid_amount": "250.00",
        "remaining_amount": "750.00",
        "payment_method": None,
        "paid_at": None,
        "annual_report_id": None,
    }


def test_work_queue_advance_payment_payload_formats_bimonthly_period(test_db):
    biz = create_business(test_db)
    due_date = date.today() + timedelta(days=3)
    create_linked_advance_payment(
        test_db,
        client_record_id=biz.client_id,
        period="2026-03",
        period_months_count=2,
        due_date=due_date,
        expected_amount=1000,
        paid_amount=0,
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)
    item = next(
        i for i in items if i.source_type == WorkQueueSourceType.ADVANCE_PAYMENT
    )

    assert item.payload["period_label"] == "מרץ–אפריל 2026"
    assert item.payload["frequency"] == "bimonthly"


def test_work_queue_advance_payment_batch_loads_all_client_identities(test_db):
    first = create_business(test_db)
    second = create_business(test_db)
    test_db.get(ClientRecord, first.client_id).office_client_number = 1
    test_db.get(ClientRecord, second.client_id).office_client_number = 3
    due_date = date.today() + timedelta(days=3)
    create_linked_advance_payment(
        test_db,
        client_record_id=first.client_id,
        period="2026-04",
        period_months_count=1,
        due_date=due_date,
        expected_amount=1000,
        paid_amount=0,
    )
    create_linked_advance_payment(
        test_db,
        client_record_id=second.client_id,
        period="2026-03",
        period_months_count=2,
        due_date=due_date,
        expected_amount=1000,
        paid_amount=0,
    )
    test_db.commit()

    items = [
        item
        for item in WorkQueueService(test_db).list_items()
        if item.source_type == WorkQueueSourceType.ADVANCE_PAYMENT
    ]

    identities = {
        item.client_record_id: (item.client_name, item.client_office_number)
        for item in items
    }
    assert identities[first.client_id][0].startswith("Task Test Client")
    assert identities[first.client_id][1] == 1
    assert identities[second.client_id][0].startswith("Task Test Client")
    assert identities[second.client_id][1] == 3


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


# ── Pagination ────────────────────────────────────────────────────────────────


def test_work_queue_pagination_limit(test_db):
    biz = create_business(test_db)
    for days_ago in [31, 32, 33]:
        test_db.add(
            Charge(
                client_record_id=biz.client_id,
                business_id=biz.id,
                amount=100,
                charge_type=ChargeType.OTHER,
                status=ChargeStatus.ISSUED,
                issued_at=date.today() - timedelta(days=days_ago),
            )
        )
    test_db.commit()

    page1 = WorkQueueService(test_db).list_items(
        client_record_id=biz.client_id, limit=2, offset=0
    )
    page2 = WorkQueueService(test_db).list_items(
        client_record_id=biz.client_id, limit=2, offset=2
    )

    assert len(page1) == 2
    assert len(page2) == 1
    assert {i.source_id for i in page1}.isdisjoint({i.source_id for i in page2})


def test_work_queue_pagination_offset_beyond_end(test_db):
    biz = create_business(test_db)
    test_db.add(
        Charge(
            client_record_id=biz.client_id,
            business_id=biz.id,
            amount=100,
            charge_type=ChargeType.OTHER,
            status=ChargeStatus.ISSUED,
            issued_at=date.today() - timedelta(days=31),
        )
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(
        client_record_id=biz.client_id, limit=50, offset=999
    )
    assert items == []


# ── business_id filter semantics ──────────────────────────────────────────────


def test_business_id_filter_hides_client_level_sources(test_db):
    """When business_id is set, VAT/annual/advance sources must not appear."""
    biz = create_business(test_db)
    due_date = date.today() - timedelta(days=1)
    payment = create_linked_advance_payment(
        test_db,
        client_record_id=biz.client_id,
        period="2026-03",
        due_date=due_date,
        expected_amount=500,
        paid_amount=0,
    )
    payment.status = AdvancePaymentStatus.PENDING
    test_db.commit()

    items = WorkQueueService(test_db).list_items(business_id=biz.id)
    source_types = {i.source_type for i in items}

    assert WorkQueueSourceType.ADVANCE_PAYMENT not in source_types
    assert WorkQueueSourceType.VAT_FILING not in source_types
    assert WorkQueueSourceType.ANNUAL_REPORT not in source_types


def test_business_id_filter_returns_unpaid_charge_for_that_business(test_db):
    biz = create_business(test_db)
    other_biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=750,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today() - timedelta(days=31),
    )
    other_charge = Charge(
        client_record_id=other_biz.client_id,
        business_id=other_biz.id,
        amount=200,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today() - timedelta(days=31),
    )
    test_db.add_all([charge, other_charge])
    test_db.commit()

    items = WorkQueueService(test_db).list_items(business_id=biz.id)
    unpaid = [i for i in items if i.source_type == WorkQueueSourceType.UNPAID_CHARGE]

    assert len(unpaid) == 1
    assert unpaid[0].source_id == charge.id


# ── Charge urgency is always OVERDUE ─────────────────────────────────────────


def test_unpaid_charge_urgency_always_overdue(test_db):
    """Charges only appear after threshold — urgency is always OVERDUE by design."""
    biz = create_business(test_db)
    test_db.add(
        Charge(
            client_record_id=biz.client_id,
            business_id=biz.id,
            amount=300,
            charge_type=ChargeType.OTHER,
            status=ChargeStatus.ISSUED,
            issued_at=date.today() - timedelta(days=31),
        )
    )
    test_db.commit()

    items = WorkQueueService(test_db).list_items(client_record_id=biz.client_id)
    charge_items = [
        i for i in items if i.source_type == WorkQueueSourceType.UNPAID_CHARGE
    ]

    assert all(i.urgency == WorkQueueUrgency.OVERDUE for i in charge_items)
