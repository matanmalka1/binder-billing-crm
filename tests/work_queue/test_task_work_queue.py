"""Work queue integration tests for persisted Task items."""

from datetime import timedelta

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.tasks.models.task import Task, TaskStatus, TaskPriority
from app.utils.time_utils import utcnow
from app.work_queue.schemas.work_queue import WorkQueueSourceType, WorkQueueUrgency
from app.work_queue.services.work_queue_service import WorkQueueService
from tests.helpers.task_helpers import create_business


def _add_task(
    db,
    title="Task",
    status=TaskStatus.OPEN,
    due_date=None,
    source_domain=None,
    source_id=None,
) -> Task:
    task = Task(
        title=title,
        status=status,
        priority=TaskPriority.NORMAL,
        due_date=due_date,
        source_domain=source_domain,
        source_id=source_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(task)
    db.commit()
    return task


# ── Inclusion ─────────────────────────────────────────────────────────────────


def test_open_task_appears_in_work_queue(test_db):
    task = _add_task(test_db, title="Open Task")
    items = WorkQueueService(test_db).list_items()
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert any(i.source_id == task.id for i in task_items)


def test_open_standalone_task_can_be_filtered_with_many_system_rows(test_db):
    biz = create_business(test_db)
    for _ in range(55):
        test_db.add(
            Charge(
                client_record_id=biz.client_id,
                business_id=biz.id,
                amount=100,
                charge_type=ChargeType.OTHER,
                status=ChargeStatus.ISSUED,
                issued_at=utcnow().date() - timedelta(days=31),
            )
        )
    task = _add_task(test_db, title="Manual task in first page")

    items = WorkQueueService(test_db).list_items(scope="manual")
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]

    assert any(i.source_id == task.id for i in task_items)
    match = next(i for i in task_items if i.source_id == task.id)
    assert match.source_type == WorkQueueSourceType.TASK
    assert match.metadata["source_domain"] is None
    assert match.metadata["source_id"] is None


def test_done_task_not_in_work_queue(test_db):
    task = _add_task(test_db, status=TaskStatus.DONE)
    items = WorkQueueService(test_db).list_items()
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert not any(i.source_id == task.id for i in task_items)


def test_canceled_task_not_in_work_queue(test_db):
    task = _add_task(test_db, status=TaskStatus.CANCELED)
    items = WorkQueueService(test_db).list_items()
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert not any(i.source_id == task.id for i in task_items)


def test_done_task_appears_in_work_queue_history(test_db):
    task = _add_task(test_db, status=TaskStatus.DONE)
    items = WorkQueueService(test_db).list_items(
        include_task_history=True,
        task_status=TaskStatus.DONE,
    )
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert any(i.source_id == task.id for i in task_items)


def test_done_task_appears_in_work_queue_history_with_many_system_rows(test_db):
    biz = create_business(test_db)
    for _ in range(55):
        test_db.add(
            Charge(
                client_record_id=biz.client_id,
                business_id=biz.id,
                amount=100,
                charge_type=ChargeType.OTHER,
                status=ChargeStatus.ISSUED,
                issued_at=utcnow().date() - timedelta(days=31),
            )
        )
    task = _add_task(test_db, title="Historical manual task", status=TaskStatus.DONE)

    items = WorkQueueService(test_db).list_items(
        include_task_history=True,
        task_status=TaskStatus.DONE,
    )
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]

    assert any(i.source_id == task.id for i in task_items)


def test_canceled_task_appears_in_work_queue_history(test_db):
    task = _add_task(test_db, status=TaskStatus.CANCELED)
    items = WorkQueueService(test_db).list_items(include_task_history=True)
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert any(i.source_id == task.id for i in task_items)


def test_done_linked_task_appears_as_task_row_in_history(test_db):
    biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=100,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=utcnow().date() - timedelta(days=31),
    )
    test_db.add(charge)
    test_db.flush()
    task = _add_task(
        test_db,
        status=TaskStatus.DONE,
        source_domain="charge",
        source_id=charge.id,
    )

    items = WorkQueueService(test_db).list_items(include_task_history=True)
    task_row = next(
        i
        for i in items
        if i.source_type == WorkQueueSourceType.TASK and i.source_id == task.id
    )

    assert task_row.source_summary is not None
    assert task_row.source_summary.source_type == "charge"
    assert task_row.source_summary.source_id == charge.id


# ── Null due_date ─────────────────────────────────────────────────────────────


def test_null_due_date_task_appears(test_db):
    task = _add_task(test_db, title="No Due Date")
    items = WorkQueueService(test_db).list_items()
    match = next(
        (
            i
            for i in items
            if i.source_type == WorkQueueSourceType.TASK and i.source_id == task.id
        ),
        None,
    )
    assert match is not None
    assert match.due_date is None
    assert match.urgency == WorkQueueUrgency.UPCOMING


def test_null_due_date_task_sorts_after_dated_task(test_db):
    _add_task(test_db, title="Dated", due_date=utcnow())
    _add_task(test_db, title="Undated", due_date=None)

    items = WorkQueueService(test_db).list_items()
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]

    dated = next(i for i in task_items if i.due_date is not None)
    undated = next(i for i in task_items if i.due_date is None)
    assert task_items.index(dated) < task_items.index(undated)


# ── Urgency from due_date ─────────────────────────────────────────────────────


def test_overdue_task_urgency(test_db):
    past = utcnow() - timedelta(days=2)
    task = _add_task(test_db, due_date=past)
    items = WorkQueueService(test_db).list_items()
    match = next(
        i
        for i in items
        if i.source_type == WorkQueueSourceType.TASK and i.source_id == task.id
    )
    assert match.urgency == WorkQueueUrgency.OVERDUE


def test_approaching_task_urgency(test_db):
    soon = utcnow() + timedelta(days=3)
    task = _add_task(test_db, due_date=soon)
    items = WorkQueueService(test_db).list_items()
    match = next(
        i
        for i in items
        if i.source_type == WorkQueueSourceType.TASK and i.source_id == task.id
    )
    assert match.urgency == WorkQueueUrgency.APPROACHING


# ── Metadata ──────────────────────────────────────────────────────────────────


def test_task_work_queue_item_metadata(test_db):
    task = Task(
        title="Payload Task",
        status=TaskStatus.OPEN,
        priority=TaskPriority.HIGH,
        description="Some details",
        assigned_to_user_id=5,
        assigned_role="advisor",
        action_key="review",
        action_payload={"key": "val"},
        source_domain="charge",
        source_id=42,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    test_db.add(task)
    test_db.commit()

    items = WorkQueueService(test_db).list_items()
    match = next(
        i
        for i in items
        if i.source_type == WorkQueueSourceType.TASK and i.source_id == task.id
    )

    assert match.title == "Payload Task"
    assert match.metadata["status"] == "open"
    assert match.metadata["priority"] == "high"
    assert match.metadata["description"] == "Some details"
    assert match.metadata["assigned_to_user_id"] == 5
    assert match.metadata["assigned_role"] == "advisor"
    assert match.metadata["action_key"] == "review"
    assert match.metadata["action_payload"] == {"key": "val"}
    assert match.metadata["source_domain"] == "charge"
    assert match.metadata["source_id"] == 42


# ── Exclusion filter ──────────────────────────────────────────────────────────


def test_exclude_task_source_type(test_db):
    _add_task(test_db)
    items = WorkQueueService(test_db).list_items(
        exclude_source_types=[WorkQueueSourceType.TASK]
    )
    assert not any(i.source_type == WorkQueueSourceType.TASK for i in items)


# ── Tasks hidden when client_record_id filter is active ──────────────────────


def test_tasks_hidden_when_client_scoped(test_db):
    _add_task(test_db, title="Global Task")
    items = WorkQueueService(test_db).list_items(client_record_id=1)
    assert not any(i.source_type == WorkQueueSourceType.TASK for i in items)
