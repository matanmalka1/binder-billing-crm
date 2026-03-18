from datetime import date

from app.annual_reports.repositories.report_lifecycle_repository import AnnualReportLifecycleRepository
from app.annual_reports.services import AnnualReportService
from app.clients.models import Client, ClientType


def _report(test_db):
    crm_client = Client(
        full_name="Lifecycle Repo Extra",
        id_number="LRX001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)
    return AnnualReportService(test_db).create_report(
        client_id=crm_client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
    )


def test_lifecycle_soft_delete_true_and_false(test_db):
    repo = AnnualReportLifecycleRepository()
    repo.db = test_db

    assert repo.soft_delete(999999, deleted_by=1) is False

    report = _report(test_db)
    assert repo.soft_delete(report.id, deleted_by=5) is True

    refreshed = AnnualReportService(test_db).repo.get_by_client_year(report.client_id, 2026)
    assert refreshed is None

