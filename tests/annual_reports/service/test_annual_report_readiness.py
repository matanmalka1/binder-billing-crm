from datetime import date, datetime

from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.services import AnnualReportService
from app.annual_reports.services.financial_service import AnnualReportFinancialService
from app.clients.models import Client, ClientType


def _create_report(db):
    client = Client(
        full_name="Readiness Client",
        id_number="565656565",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    svc = AnnualReportService(db)
    return svc.create_report(
        client_id=client.id,
        tax_year=2026,
        client_type="corporation",
        created_by=1,
        created_by_name="Tester",
        deadline_type="standard",
    )


def test_readiness_reports_issues_when_missing_data(test_db):
    report = _create_report(test_db)
    service = AnnualReportFinancialService(test_db)

    result = service.get_readiness_check(report.id)

    assert result.is_ready is False
    assert "לא הוזנו נתוני הכנסה לדוח" in result.issues
    assert "חסר חישוב מס — יש למלא חוב מס או החזר מס" in result.issues
    assert "הדוח לא אושר על ידי הלקוח" in result.issues
    assert result.completion_pct < 100


def test_readiness_passes_when_all_checks_complete(test_db):
    report = _create_report(test_db)
    service = AnnualReportFinancialService(test_db)

    # Provide income so taxable income > 0
    service.add_income(report.id, source_type="salary", amount=10_000)
    # Provide tax result and client approval
    AnnualReportDetailRepository(test_db).upsert(
        report.id,
        tax_due_amount=1000,
        client_approved_at=datetime.utcnow(),
    )

    result = service.get_readiness_check(report.id)

    assert result.is_ready is True
    assert result.issues == []
    assert result.completion_pct == 100.0
