from datetime import date, timedelta

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus
from app.tasks.schemas.task import TaskType, TaskUrgency
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


def test_tasks_sorted_by_due_date(test_db):
    biz = create_business(test_db)
    today = date.today()
    _make_deadline(test_db, biz.client_id, DeadlineType.ADVANCE_PAYMENT, today + timedelta(days=10))
    _make_deadline(test_db, biz.client_id, DeadlineType.VAT, today + timedelta(days=2))
    test_db.commit()

    tasks = TaskService(test_db).get_tasks(client_record_id=biz.client_id)
    due_dates = [t.due_date for t in tasks]
    assert due_dates == sorted(due_dates)
