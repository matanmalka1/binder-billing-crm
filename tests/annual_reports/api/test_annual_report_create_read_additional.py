from datetime import date

from app.annual_reports.services import AnnualReportService
from app.clients.models import Client


def _create_report(db) -> int:
    crm_client = Client(
        full_name="AR CreateRead Additional",
        id_number="ARCRA001",

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


def test_get_report_not_found_and_delete_paths(client, test_db, advisor_headers):
    missing = client.get("/api/v1/annual-reports/999999", headers=advisor_headers)
    assert missing.status_code == 404

    report_id = _create_report(test_db)
    get_ok = client.get(f"/api/v1/annual-reports/{report_id}", headers=advisor_headers)
    assert get_ok.status_code == 200

    del_ok = client.delete(f"/api/v1/annual-reports/{report_id}", headers=advisor_headers)
    assert del_ok.status_code == 204

    del_missing = client.delete("/api/v1/annual-reports/999999", headers=advisor_headers)
    assert del_missing.status_code == 404
