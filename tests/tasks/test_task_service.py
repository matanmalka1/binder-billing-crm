from datetime import date, timedelta

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.tasks.schemas.task import DeadlineTask, TaskType, TaskUrgency
from app.tasks.services.task_service import TaskService
from tests.tax_deadline.factories import create_business


def _make_deadline(db, client_record_id: int, deadline_type: DeadlineType, due_date: date) -> TaxDeadline:
    td = TaxDeadline(
        client_record_id=client_record_id,
        deadline_type=deadline_type,
        due_date=due_date,
        status=TaxDeadlineStatus.PENDING,
    )
    db.add(td)
    db.flush()
    return td


def test_tax_deadline_task_appears_within_window(test_db):
    biz = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=7))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    tax_tasks = [t for t in tasks if t.source_type == TaskType.TAX_DEADLINE]
    assert len(tax_tasks) == 1
    assert tax_tasks[0].urgency == TaskUrgency.APPROACHING


def test_tax_deadline_task_outside_window_excluded(test_db):
    biz = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=30))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    tax_tasks = [t for t in tasks if t.source_type == TaskType.TAX_DEADLINE]
    assert len(tax_tasks) == 0


def test_completed_deadline_excluded(test_db):
    biz = create_business(test_db)
    today = date.today()
    td = _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=3))
    td.status = TaxDeadlineStatus.COMPLETED
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    assert not any(t.source_type == TaskType.TAX_DEADLINE for t in tasks)


def test_overdue_deadline_urgency(test_db):
    biz = create_business(test_db)
    td = _make_deadline(test_db, biz.client_id, DeadlineType.ADVANCE_PAYMENT, date.today() - timedelta(days=1))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    overdue = [t for t in tasks if t.source_id == td.id]
    assert len(overdue) == 1
    assert overdue[0].urgency == TaskUrgency.OVERDUE


def test_unpaid_charge_task_after_threshold(test_db):
    biz = create_business(test_db)
    threshold_days = 30
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=500,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today() - timedelta(days=threshold_days + 1),
    )
    test_db.add(charge)
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    unpaid = [t for t in tasks if t.source_type == TaskType.UNPAID_CHARGE]
    assert len(unpaid) == 1
    assert unpaid[0].source_id == charge.id
    assert unpaid[0].urgency == TaskUrgency.OVERDUE


def test_unpaid_charge_before_threshold_excluded(test_db):
    biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=200,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today() - timedelta(days=10),
    )
    test_db.add(charge)
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    unpaid = [t for t in tasks if t.source_type == TaskType.UNPAID_CHARGE]
    assert len(unpaid) == 0


def test_get_tasks_filters_by_client_record_id(test_db):
    biz_a = create_business(test_db)
    biz_b = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz_a.client_id, DeadlineType.VAT, today + timedelta(days=3))
    _make_deadline(test_db, biz_b.client_id, DeadlineType.VAT, today + timedelta(days=3))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz_a.client_id)
    assert all(t.client_record_id == biz_a.client_id for t in tasks)


def test_unified_includes_tasks_and_reminders(test_db):
    from app.reminders.models.reminder import Reminder, ReminderStatus, ReminderType
    biz = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=5))
    reminder = Reminder(
        client_record_id=biz.client_id,
        reminder_type=ReminderType.CUSTOM,
        status=ReminderStatus.PENDING,
        target_date=today + timedelta(days=2),
        days_before=0,
        send_on=today,
        message="תזכורת בדיקה",
    )
    test_db.add(reminder)
    test_db.commit()

    items = TaskService(test_db).get_unified(client_record_id=biz.client_id)
    types = {i.item_type for i in items}
    assert "task" in types
    assert "reminder" in types


def test_unified_advance_payment_includes_source_payload(test_db):
    biz = create_business(test_db)
    due_date = date.today() - timedelta(days=1)
    payment = AdvancePayment(
        client_record_id=biz.client_id,
        period="2026-02",
        period_months_count=1,
        due_date=due_date,
        expected_amount=1000,
        paid_amount=250,
        status=AdvancePaymentStatus.PARTIAL,
    )
    test_db.add(payment)
    test_db.commit()

    items = TaskService(test_db).get_unified(client_record_id=biz.client_id)
    item = next(i for i in items if i.source_type == TaskType.ADVANCE_PAYMENT.value)

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


def test_unified_tasks_api_returns_advance_payment_payload(
    client, test_db, advisor_headers
):
    biz = create_business(test_db)
    due_date = date.today() - timedelta(days=1)
    payment = AdvancePayment(
        client_record_id=biz.client_id,
        period="2026-02",
        period_months_count=1,
        due_date=due_date,
        expected_amount=1000,
        paid_amount=250,
        status=AdvancePaymentStatus.PARTIAL,
    )
    test_db.add(payment)
    test_db.commit()

    response = client.get(
        "/api/v1/tasks/unified"
        "?exclude_source_types=vat_filing&exclude_source_types=annual_report",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    item = next(i for i in response.json() if i["source_type"] == "advance_payment")
    assert item["payload"]["period"] == "2026-02"
    assert item["payload"]["remaining_amount"] == "750.00"


def test_unified_excludes_requested_task_source_types(test_db, monkeypatch):
    service = TaskService(test_db)
    vat_task = DeadlineTask(
        source_type=TaskType.VAT_FILING,
        source_id=1,
        label='מע"מ לא הוגש: 2026-04',
        due_date=date.today(),
        urgency=TaskUrgency.APPROACHING,
        client_record_id=1,
    )
    annual_task = DeadlineTask(
        source_type=TaskType.ANNUAL_REPORT,
        source_id=2,
        label="דוח שנתי 2025",
        due_date=date.today(),
        urgency=TaskUrgency.APPROACHING,
        client_record_id=1,
    )

    monkeypatch.setattr(service, "_tax_deadline_tasks", lambda client_record_id: [])
    monkeypatch.setattr(service, "_vat_filing_tasks", lambda client_record_id: [vat_task])
    monkeypatch.setattr(service, "_annual_report_tasks", lambda client_record_id: [annual_task])
    monkeypatch.setattr(service, "_advance_payment_tasks", lambda client_record_id: [])
    monkeypatch.setattr(service, "_unpaid_charge_tasks", lambda client_record_id, business_id: [])

    items = service.get_unified(
        exclude_source_types=[TaskType.VAT_FILING, TaskType.ANNUAL_REPORT]
    )

    assert items == []


def test_get_tasks_skips_excluded_builders(test_db, monkeypatch):
    service = TaskService(test_db)
    monkeypatch.setattr(service, "_tax_deadline_tasks", lambda client_record_id: [])
    monkeypatch.setattr(service, "_vat_filing_tasks", lambda client_record_id: [])
    monkeypatch.setattr(
        service,
        "_annual_report_tasks",
        lambda client_record_id: (_ for _ in ()).throw(AssertionError("should skip")),
    )
    monkeypatch.setattr(service, "_advance_payment_tasks", lambda client_record_id: [])
    monkeypatch.setattr(service, "_unpaid_charge_tasks", lambda client_record_id, business_id: [])

    assert service.get_tasks(exclude_source_types=[TaskType.ANNUAL_REPORT]) == []


def test_tasks_sorted_by_due_date(test_db):
    biz = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz.client_id, DeadlineType.ADVANCE_PAYMENT, today + timedelta(days=10))
    _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=2))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    due_dates = [t.due_date for t in tasks]
    assert due_dates == sorted(due_dates)
