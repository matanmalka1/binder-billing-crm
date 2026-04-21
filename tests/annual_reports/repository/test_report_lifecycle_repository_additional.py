from datetime import date

from app.annual_reports.services.annual_report_service import AnnualReportService
from tests.helpers.identity import seed_client_identity


def _report(test_db):
    crm_client = seed_client_identity(test_db, full_name="Lifecycle Repo Extra", id_number="LRX001")
    return AnnualReportService(test_db).create_report(
        client_record_id=crm_client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
    )


def test_lifecycle_soft_delete_true_and_false(test_db):
    repo = AnnualReportService(test_db).repo

    assert repo.soft_delete(999999, deleted_by=1) is False

    report = _report(test_db)
    assert repo.soft_delete(report.id, deleted_by=5) is True

    refreshed = AnnualReportService(test_db).repo.get_by_client_record_year(report.client_record_id, 2026)
    assert refreshed is None
