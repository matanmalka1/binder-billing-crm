from datetime import date
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.annual_reports.services import AnnualReportService
from app.clients.models import Client, ClientType


def _create_report(db):
    client = Client(
        full_name="Advances Client",
        id_number="878787878",
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


def test_advances_summary_reports_refund_when_advances_exceed_tax(client, test_db, advisor_headers):
    report = _create_report(test_db)
    # No income/expense → tax_after_credits = 0

    repo = AdvancePaymentRepository(test_db)
    payment = repo.create(
        client_id=report.client_id,
        year=2026,
        month=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100.00"),
        paid_amount=Decimal("100.00"),
    )
    repo.update(payment, status=AdvancePaymentStatus.PAID, paid_amount=Decimal("100.00"))

    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/advances-summary",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_advances_paid"] == 100.0
    assert body["advances_count"] == 1
    assert body["balance_type"] == "refund"
    assert body["final_balance"] == -100.0


def test_advances_summary_zero_balance_without_paid_advances(client, test_db, advisor_headers):
    report = _create_report(test_db)
    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/advances-summary",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["balance_type"] == "zero"


def test_advances_summary_not_found(client, advisor_headers):
    resp = client.get("/api/v1/annual-reports/999999/advances-summary", headers=advisor_headers)
    assert resp.status_code == 404
