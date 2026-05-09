
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


def test_create_task_with_optional_fields(client, advisor_headers):
    resp = client.post(
        "/api/v1/tasks",
        headers=advisor_headers,
        json={
            "title": "Rich Task",
            "description": "Some details",
            "priority": "high",
            "source_domain": "charge",
            "source_id": 7,
            "action_key": "review_charge",
            "action_payload": {"charge_id": 7},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == "high"
    assert data["source_domain"] == "charge"
    assert data["action_payload"] == {"charge_id": 7}


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

def test_start_task(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Start Me"}
    ).json()
    resp = client.post(
        f"/api/v1/tasks/{created['id']}/start", headers=advisor_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


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
    resp = client.post(
        f"/api/v1/tasks/{created['id']}/cancel", headers=advisor_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "canceled"
    assert data["canceled_at"] is not None


def test_start_done_task_rejected(client, advisor_headers):
    created = client.post(
        "/api/v1/tasks", headers=advisor_headers, json={"title": "Done"}
    ).json()
    client.post(f"/api/v1/tasks/{created['id']}/complete", headers=advisor_headers)
    resp = client.post(
        f"/api/v1/tasks/{created['id']}/start", headers=advisor_headers
    )
    assert resp.status_code == 409


def test_secretary_can_access_tasks(client, secretary_headers):
    resp = client.get("/api/v1/tasks", headers=secretary_headers)
    assert resp.status_code == 200
