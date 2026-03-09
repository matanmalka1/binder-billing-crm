from decimal import Decimal
from datetime import date
from itertools import count

from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.services import AnnualReportService
from app.annual_reports.services.tax_engine import calculate_tax
from app.clients.models import Client, ClientType


_client_seq = count(1)


def _create_report(db):
    client = Client(
        full_name="AR Finance Client",
        id_number=f"55555555{next(_client_seq)}",
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
    return report


def test_financial_summary_totals(client, test_db, advisor_headers):
    report = _create_report(test_db)

    # Income and expense lines
    client.post(
        f"/api/v1/annual-reports/{report.id}/income",
        headers=advisor_headers,
        json={"source_type": "salary", "amount": 100000, "description": "Gross income"},
    )
    client.post(
        f"/api/v1/annual-reports/{report.id}/expenses",
        headers=advisor_headers,
        json={"category": "other", "amount": 20000, "description": "Office spend"},
    )

    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/financials",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_income"] == 100000
    assert body["gross_expenses"] == 20000
    assert body["recognized_expenses"] == 20000
    assert body["taxable_income"] == 80000
    assert len(body["income_lines"]) == 1
    assert len(body["expense_lines"]) == 1


def test_tax_calculation_includes_pension_and_donations(client, test_db, advisor_headers):
    report = _create_report(test_db)

    client.post(
        f"/api/v1/annual-reports/{report.id}/income",
        headers=advisor_headers,
        json={"source_type": "salary", "amount": 100000},
    )
    client.post(
        f"/api/v1/annual-reports/{report.id}/expenses",
        headers=advisor_headers,
        json={"category": "other", "amount": 20000},
    )

    # Set credit points & deductions on report detail
    AnnualReportDetailRepository(test_db).upsert(
        report.id,
        credit_points=Decimal("2.25"),
        pension_contribution=Decimal("6000"),
        donation_amount=Decimal("1000"),
        other_credits=Decimal("500"),
    )

    resp = client.get(
        f"/api/v1/annual-reports/{report.id}/tax-calculation",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()

    expected = calculate_tax(
        taxable_income=80000,
        credit_points=2.25,
        pension_deduction=6000,
        donation_amount=1000,
        other_credits=500,
    )

    assert payload["taxable_income"] == expected.taxable_income
    assert payload["pension_deduction"] == expected.pension_deduction
    assert payload["tax_before_credits"] == expected.tax_before_credits
    assert payload["credit_points_value"] == expected.credit_points_value
    assert payload["donation_credit"] == expected.donation_credit
    assert payload["other_credits"] == expected.other_credits
    assert payload["tax_after_credits"] == expected.tax_after_credits
    assert abs(payload["effective_rate"] - expected.effective_rate) < 1e-6


def test_add_income_invalid_type_returns_400(client, test_db, advisor_headers):
    report = _create_report(test_db)

    resp = client.post(
        f"/api/v1/annual-reports/{report.id}/income",
        headers=advisor_headers,
        json={"source_type": "invalid_type", "amount": 1000},
    )

    assert resp.status_code == 400
    assert resp.json()["error"] == "ANNUAL_REPORT.INVALID_TYPE"
