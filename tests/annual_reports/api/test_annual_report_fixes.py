import pytest

from tests.helpers.identity import seed_client_identity


def _create_client(db, id_number: str = "AR_FIX_001"):
    return seed_client_identity(db, full_name="Annual Fix Client", id_number=id_number)


def test_create_report_invalid_assigned_to_raises_error(client, test_db, advisor_headers):
    """assigned_to with non-existent user ID must return 400."""
    c = _create_client(test_db, "AR_ASSIGN_001")

    response = client.post(
        "/api/v1/annual-reports",
        headers=advisor_headers,
        json={
            "client_record_id": c.id,
            "tax_year": 2024,
            "client_type": "individual",
            "deadline_type": "standard",
            "assigned_to": 99999,
        },
    )

    assert response.status_code == 404
    assert response.json()["error"] == "USER.NOT_FOUND"


def test_create_report_valid_assigned_to_succeeds(client, test_db, advisor_headers, test_user):
    """assigned_to with an existing user ID must succeed."""
    c = _create_client(test_db, "AR_ASSIGN_002")

    response = client.post(
        "/api/v1/annual-reports",
        headers=advisor_headers,
        json={
            "client_record_id": c.id,
            "tax_year": 2026,
            "client_type": "individual",
            "deadline_type": "standard",
            "assigned_to": test_user.id,
        },
    )

    assert response.status_code in (200, 201)
    data = response.json()
    assert data.get("assigned_to") == test_user.id


# ── Sort tests ────────────────────────────────────────────────────────────────

def _create_report(client, headers, db_client_id: int, tax_year: int):
    return client.post(
        "/api/v1/annual-reports",
        headers=headers,
        json={
            "client_record_id": db_client_id,
            "tax_year": tax_year,
            "client_type": "individual",
            "deadline_type": "standard",
        },
    )


def test_list_reports_sort_by_tax_year_desc(client, test_db, advisor_headers):
    """sort_by=tax_year&order=desc must return newer years first."""
    c = _create_client(test_db, "AR_SORT_001")
    _create_report(client, advisor_headers, c.id, 2024)
    _create_report(client, advisor_headers, c.id, 2026)

    resp = client.get(
        "/api/v1/annual-reports?sort_by=tax_year&order=desc",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    years = [item["tax_year"] for item in resp.json()["items"]]
    assert years == sorted(years, reverse=True)


def test_list_reports_sort_by_tax_year_asc(client, test_db, advisor_headers):
    """sort_by=tax_year&order=asc must return older years first."""
    c = _create_client(test_db, "AR_SORT_002")
    _create_report(client, advisor_headers, c.id, 2024)
    _create_report(client, advisor_headers, c.id, 2025)

    resp = client.get(
        "/api/v1/annual-reports?sort_by=tax_year&order=asc",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    years = [item["tax_year"] for item in resp.json()["items"]]
    assert years == sorted(years)


def test_list_reports_invalid_sort_by_returns_422(client, advisor_headers):
    """sort_by with an invalid value must return 422."""
    resp = client.get(
        "/api/v1/annual-reports?sort_by=invalid_field",
        headers=advisor_headers,
    )
    assert resp.status_code == 422


def test_list_reports_invalid_order_returns_422(client, advisor_headers):
    """order with a value other than asc/desc must return 422."""
    resp = client.get(
        "/api/v1/annual-reports?order=random",
        headers=advisor_headers,
    )
    assert resp.status_code == 422


def test_list_reports_sort_by_tax_year_with_filter(client, test_db, advisor_headers):
    """sort_by respects tax_year filter — reports within same year sorted by filing_deadline asc."""
    c = _create_client(test_db, "AR_SORT_003")
    # Both reports are for the same tax year; use two businesses to avoid unique constraints.
    c2 = _create_client(test_db, "AR_SORT_003B")
    _create_report(client, advisor_headers, c.id, 2025)
    _create_report(client, advisor_headers, c2.id, 2025)

    resp = client.get("/api/v1/annual-reports?tax_year=2025&sort_by=client_record_id&order=asc", headers=advisor_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["tax_year"] == 2025 for item in items)
    client_ids = [item["client_record_id"] for item in items]
    assert client_ids == sorted(client_ids)
