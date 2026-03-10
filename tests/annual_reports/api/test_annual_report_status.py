from datetime import date

import pytest

from app.annual_reports.models import AnnualReportStatus, DeadlineType
from app.annual_reports.services import AnnualReportService
from app.clients.models import Client, ClientType


def _create_report(db) -> int:
    client = Client(
        full_name="Status Client",
        id_number="989898989",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    svc = AnnualReportService(db)
    report = svc.create_report(
        client_id=client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
        notes=None,
    )
    return report.id


def test_valid_status_transition(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report_id}/status",
        headers=advisor_headers,
        json={"status": "collecting_docs"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "collecting_docs"


def test_invalid_status_transition_returns_400(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report_id}/status",
        headers=advisor_headers,
        json={"status": "submitted"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "ANNUAL_REPORT.INVALID_STATUS"


def test_update_deadline_sets_extended_date(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report_id}/deadline",
        headers=advisor_headers,
        json={"deadline_type": "extended", "custom_deadline_note": "Extend for rep"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deadline_type"] == "extended"
    # Extended deadline should be Jan 31 two years after tax year
    assert body["filing_deadline"].startswith("2028-01-31")


def test_get_status_history_returns_ordered_entries(client, test_db, advisor_headers):
    report_id = _create_report(test_db)
    client.post(
        f"/api/v1/annual-reports/{report_id}/status",
        headers=advisor_headers,
        json={"status": "collecting_docs"},
    )
    client.post(
        f"/api/v1/annual-reports/{report_id}/status",
        headers=advisor_headers,
        json={"status": "docs_complete"},
    )

    resp = client.get(
        f"/api/v1/annual-reports/{report_id}/history",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    assert body[-2]["to_status"] == "collecting_docs"
    assert body[-1]["to_status"] == "docs_complete"
    assert body[-1]["annual_report_id"] == report_id


def test_get_status_history_returns_404_for_missing_report(client, advisor_headers):
    resp = client.get(
        "/api/v1/annual-reports/999999/history",
        headers=advisor_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "ANNUAL_REPORT.NOT_FOUND"


def test_submit_endpoint_exists(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report_id}/submit",
        headers=advisor_headers,
        json={},
    )
    assert resp.status_code != 404


def test_submit_invalid_transition_returns_400(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report_id}/submit",
        headers=advisor_headers,
        json={},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "ANNUAL_REPORT.INVALID_STATUS"


def test_submit_not_found_returns_404(client, advisor_headers):
    resp = client.post(
        "/api/v1/annual-reports/999999/submit",
        headers=advisor_headers,
        json={},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "ANNUAL_REPORT.NOT_FOUND"
