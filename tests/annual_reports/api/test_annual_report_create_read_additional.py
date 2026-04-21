from datetime import date

from app.annual_reports.services.annual_report_service import AnnualReportService
from tests.helpers.identity import seed_client_identity


def _create_report(db) -> int:
    crm_client = seed_client_identity(db, full_name="AR CreateRead Additional", id_number="ARCRA001")

    report = AnnualReportService(db).create_report(
        client_record_id=crm_client.id,
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
    body = get_ok.json()
    assert body["client_record_id"] is not None
    assert body["client_name"] == "AR CreateRead Additional"

    del_ok = client.delete(f"/api/v1/annual-reports/{report_id}", headers=advisor_headers)
    assert del_ok.status_code == 204

    del_missing = client.delete("/api/v1/annual-reports/999999", headers=advisor_headers)
    assert del_missing.status_code == 404
