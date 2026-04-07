from datetime import date

from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.models.client import Client


def _create_report(db) -> int:
    crm_client = Client(
        full_name="AR Kanban Transition",
        id_number="ARKAN001",

    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)

    report = AnnualReportService(db).create_report(
        business_id=crm_client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
        notes=None,
    )
    return report.id


def test_transition_stage_success_and_not_found(client, test_db, advisor_headers):
    report_id = _create_report(test_db)

    ok = client.post(
        f"/api/v1/annual-reports/{report_id}/transition",
        headers=advisor_headers,
        json={"to_stage": "material_collection"},
    )
    assert ok.status_code == 200

    missing = client.post(
        "/api/v1/annual-reports/999999/transition",
        headers=advisor_headers,
        json={"to_stage": "material_collection"},
    )
    assert missing.status_code == 404
