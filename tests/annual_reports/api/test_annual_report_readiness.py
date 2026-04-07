from datetime import date
from itertools import count

from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.clients.models.client import Client

_client_seq = count(1)


def _create_report(db):
    client = Client(
        full_name=f"Readiness API Client {next(_client_seq)}",
        id_number=f"34343434{next(_client_seq)}",

    )
    db.add(client)
    db.commit()
    db.refresh(client)

    svc = AnnualReportService(db)
    return svc.create_report(
        business_id=client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
    )


def test_readiness_endpoint_returns_issues(client, test_db, advisor_headers):
    report = _create_report(test_db)

    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/readiness",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is False
    assert len(data["issues"]) >= 2


def test_readiness_endpoint_ready_when_data_present(client, test_db, advisor_headers):
    report = _create_report(test_db)
    # Add income via service
    from app.annual_reports.services.financial_service import AnnualReportFinancialService

    AnnualReportFinancialService(test_db).add_income(
        report.id, source_type="salary", amount=5000
    )
    AnnualReportService(test_db).repo.update(report.id, tax_due=100)
    AnnualReportDetailRepository(test_db).upsert(
        report.id,
        client_approved_at=date.today(),
    )

    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/readiness",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ready"] is True
    assert data["issues"] == []
