"""Work queue integration tests for persisted Task items."""

from datetime import timedelta

from app.tasks.models.task import Task, TaskStatus, TaskPriority
from app.utils.time_utils import utcnow
from app.work_queue.schemas.work_queue import WorkQueueSourceType, WorkQueueUrgency
from app.work_queue.services.work_queue_service import WorkQueueService


def _add_task(db, title="Task", status=TaskStatus.OPEN, due_date=None) -> Task:
    task = Task(
        title=title,
        status=status,
        priority=TaskPriority.NORMAL,
        due_date=due_date,
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


def test_in_progress_task_appears_in_work_queue(test_db):
    task = _add_task(test_db, status=TaskStatus.IN_PROGRESS)
    items = WorkQueueService(test_db).list_items()
    task_items = [i for i in items if i.source_type == WorkQueueSourceType.TASK]
    assert any(i.source_id == task.id for i in task_items)


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


# ── Payload ───────────────────────────────────────────────────────────────────


def test_task_work_queue_item_payload(test_db):
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

    assert match.label == "Payload Task"
    assert match.payload["status"] == "open"
    assert match.payload["priority"] == "high"
    assert match.payload["description"] == "Some details"
    assert match.payload["assigned_to_user_id"] == 5
    assert match.payload["assigned_role"] == "advisor"
    assert match.payload["action_key"] == "review"
    assert match.payload["action_payload"] == {"key": "val"}
    assert match.payload["source_domain"] == "charge"
    assert match.payload["source_id"] == 42


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
