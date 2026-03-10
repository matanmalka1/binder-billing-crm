from datetime import date

from app.annual_reports.services import AnnualReportService
from app.clients.models import Client, ClientType


def _create_report(db) -> int:
    client = Client(
        full_name="Schedule Client",
        id_number="989898988",
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


def test_get_schedules_returns_entries_for_report(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    create_resp = client.post(
        f"/api/v1/annual-reports/{report_id}/schedules",
        headers=advisor_headers,
        json={"schedule": "schedule_b", "notes": "First schedule"},
    )
    assert create_resp.status_code == 201

    resp = client.get(
        f"/api/v1/annual-reports/{report_id}/schedules",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert any(item["schedule"] == "schedule_b" for item in body)
    assert all(item["annual_report_id"] == report_id for item in body)


def test_get_schedules_returns_404_for_missing_report(client, advisor_headers):
    resp = client.get(
        "/api/v1/annual-reports/999999/schedules",
        headers=advisor_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "ANNUAL_REPORT.NOT_FOUND"
