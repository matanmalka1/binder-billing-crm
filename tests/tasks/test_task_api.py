from datetime import date

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.tasks.repositories.task_repository import TaskRepository
from app.utils.time_utils import utcnow
from tests.helpers.task_helpers import create_business


# ── Create ────────────────────────────────────────────────────────────────────


def test_create_task_returns_201(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "New Task"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Task"
    assert data["status"] == "open"
    assert data["priority"] == "normal"


def test_create_standalone_task_is_open_active_and_unlinked(
    client, test_db, advisor_headers
):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Standalone queue task"},
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    task = TaskRepository(test_db).get_by_id(task_id)
    assert task is not None
    assert task.deleted_at is None
    assert task.status.value == "open"
    assert task.source_domain is None
    assert task.source_id is None


def test_create_standalone_task_appears_in_work_queue_api(
    client, advisor_headers
):
    created = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Find me in queue"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    resp = client.get("/api/v1/work-queue", headers=advisor_headers)
    assert resp.status_code == 200
    items = resp.json()
    match = next(
        (
            item
            for item in items
            if item["source_type"] == "task" and item["source_id"] == task_id
        ),
        None,
    )
    assert match is not None
    assert match["title"] == "Find me in queue"
    assert match["metadata"]["source_domain"] is None
    assert match["metadata"]["source_id"] is None


def test_create_task_persists_due_date(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Due task", "due_date": "2026-06-15T00:00:00Z"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["due_date"].startswith("2026-06-15T00:00:00")


def test_update_task_persists_due_date(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Due update"},
    ).json()

    resp = client.patch(
        f"/api/v1/tasks/{created['id']}",
        headers=advisor_headers,
        json={"due_date": "2026-07-20T00:00:00Z"},
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"].startswith("2026-07-20T00:00:00")


def test_work_queue_task_row_exposes_due_date_after_create(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Queue due task", "due_date": "2026-08-10T00:00:00Z"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    resp = client.get("/api/v1/work-queue", headers=advisor_headers)
    assert resp.status_code == 200
    item = next(
        row
        for row in resp.json()
        if row["source_type"] == "task" and row["source_id"] == task_id
    )
    assert item["due_date"] == "2026-08-10"


def test_completed_standalone_task_appears_in_work_queue_history_api(
    client, advisor_headers
):
    created = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Completed history task"},
    ).json()
    complete_resp = client.post(
        f"/api/v1/tasks/{created['id']}/complete",
        headers=advisor_headers,
    )
    assert complete_resp.status_code == 200

    active_resp = client.get("/api/v1/work-queue", headers=advisor_headers)
    assert active_resp.status_code == 200
    assert not any(
        row["source_type"] == "task" and row["source_id"] == created["id"]
        for row in active_resp.json()
    )

    history_resp = client.get(
        "/api/v1/work-queue?include_task_history=true",
        headers=advisor_headers,
    )
    assert history_resp.status_code == 200
    assert any(
        row["source_type"] == "task" and row["source_id"] == created["id"]
        for row in history_resp.json()
    )


def test_create_task_with_optional_fields(client, test_db, advisor_headers):
    biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=100,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today(),
    )
    test_db.add(charge)
    test_db.commit()
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={
            "title": "Rich Task",
            "description": "Some details",
            "priority": "high",
            "source_domain": "charge",
            "source_id": charge.id,
            "action_key": "review_charge",
            "action_payload": {"charge_id": charge.id},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == "high"
    assert data["source_domain"] == "charge"
    assert data["action_payload"] == {"charge_id": charge.id}


def test_create_task_requires_title(client, advisor_headers):
    resp = client.post("/api/v1/tasks", headers=advisor_headers, json={})
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────


def test_list_tasks_empty(client, advisor_headers):
    resp = client.get("/api/v1/tasks", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_tasks_with_status_filter(client, advisor_headers):
    client.post("/api/v1/tasks", headers=advisor_headers, json={"title": "T1"})
    client.post("/api/v1/tasks", headers=advisor_headers, json={"title": "T2"})

    resp = client.get("/api/v1/tasks?status=open", headers=advisor_headers)
    data = resp.json()
    assert data["total"] == 2
    assert all(i["status"] == "open" for i in data["items"])


# ── Get ───────────────────────────────────────────────────────────────────────


def test_get_task(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Get Me"}
    ).json()
    resp = client.get(f"/api/v1/tasks/{created['id']}", headers=advisor_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_nonexistent_task(client, advisor_headers):
    resp = client.get("/api/v1/tasks/99999", headers=advisor_headers)
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────


def test_update_task_title(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Old Title"}
    ).json()
    resp = client.patch(
        f"/api/v1/tasks/{created['id']}",
        headers=advisor_headers,
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


# ── Lifecycle ─────────────────────────────────────────────────────────────────


def test_complete_task(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Complete Me"}
    ).json()
    resp = client.post(
        f"/api/v1/tasks/{created['id']}/complete", headers=advisor_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None


def test_cancel_task(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Cancel Me"}
    ).json()
    resp = client.post(f"/api/v1/tasks/{created['id']}/cancel", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "canceled"
    assert data["canceled_at"] is not None


def test_delete_task_soft_deletes(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Delete Me"}
    ).json()
    resp = client.delete(f"/api/v1/tasks/{created['id']}", headers=advisor_headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/api/v1/tasks/{created['id']}", headers=advisor_headers)
    assert get_resp.status_code == 404


def test_create_task_rejects_unknown_source_domain(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Bad source", "source_domain": "unpaid_charge", "source_id": 1},
    )
    assert resp.status_code == 400


def test_create_task_rejects_partial_source_link_domain_only(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Bad source", "source_domain": "charge"},
    )
    assert resp.status_code == 400


def test_create_task_rejects_partial_source_link_id_only(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Bad source", "source_id": 1},
    )
    assert resp.status_code == 400


def test_create_task_rejects_missing_linked_source(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={
            "title": "Missing source",
            "source_domain": "charge",
            "source_id": 99999,
        },
    )
    assert resp.status_code == 404


def test_create_task_rejects_deleted_linked_source(client, test_db, advisor_headers):
    biz = create_business(test_db)
    charge = Charge(
        client_record_id=biz.client_id,
        business_id=biz.id,
        amount=100,
        charge_type=ChargeType.OTHER,
        status=ChargeStatus.ISSUED,
        issued_at=date.today(),
        deleted_at=utcnow(),
    )
    test_db.add(charge)
    test_db.commit()

    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={
            "title": "Deleted source",
            "source_domain": "charge",
            "source_id": charge.id,
        },
    )
    assert resp.status_code == 404


def test_secretary_can_access_tasks(client, secretary_headers):
    resp = client.get("/api/v1/tasks", headers=secretary_headers)
    assert resp.status_code == 200


def test_secretary_can_manage_tasks(client, secretary_headers):
    created = client.post(
        "/api/v1/tasks", headers=secretary_headers, json={"title": "Secretary task"}
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    assert client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=secretary_headers,
        json={"title": "Updated by secretary"},
    ).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/complete", headers=secretary_headers).status_code == 200

    deletable = client.post(
        "/api/v1/tasks", headers=secretary_headers, json={"title": "Delete by secretary"}
    ).json()
    assert client.delete(f"/api/v1/tasks/{deletable['id']}", headers=secretary_headers).status_code == 204


# ── Pagination total > page_size ──────────────────────────────────────────────


def test_list_pagination_total_reflects_all_items(client, advisor_headers):
    for i in range(5):
        client.post(
            "/api/v1/tasks", headers=advisor_headers, json={"title": f"Task {i}"}
        )

    resp = client.get("/api/v1/tasks?page=1&page_size=3", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 3


def test_list_pagination_page2(client, advisor_headers):
    for i in range(5):
        client.post(
            "/api/v1/tasks", headers=advisor_headers, json={"title": f"Task {i}"}
        )

    p1 = client.get("/api/v1/tasks?page=1&page_size=3", headers=advisor_headers).json()
    p2 = client.get("/api/v1/tasks?page=2&page_size=3", headers=advisor_headers).json()

    assert len(p1["items"]) == 3
    assert len(p2["items"]) == 2
    ids1 = {i["id"] for i in p1["items"]}
    ids2 = {i["id"] for i in p2["items"]}
    assert ids1.isdisjoint(ids2)


# ── assigned_role validation ──────────────────────────────────────────────────


def test_create_task_valid_assigned_role_advisor(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Role Task", "assigned_role": "advisor"},
    )
    assert resp.status_code == 201
    assert resp.json()["assigned_role"] == "advisor"


def test_create_task_valid_assigned_role_secretary(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Role Task", "assigned_role": "secretary"},
    )
    assert resp.status_code == 201


def test_create_task_invalid_assigned_role_rejected(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={"title": "Bad Role", "assigned_role": "superadmin"},
    )
    assert resp.status_code == 422


def test_update_task_invalid_assigned_role_rejected(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Task"}
    ).json()
    resp = client.patch(
        f"/api/v1/tasks/{created['id']}",
        headers=advisor_headers,
        json={"assigned_role": "manager"},
    )
    assert resp.status_code == 422
