from datetime import date
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.annual_reports.services.financial_service import AnnualReportFinancialService
from app.clients.models.client import Client
from app.core.exceptions import AppError, ConflictError


def _client(db, suffix="1"):
    c = Client(
        full_name=f"AR create extra {suffix}",
        id_number=f"ARCE{suffix}",

    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_create_report_validation_errors(test_db):
    c = _client(test_db, "A")
    service = AnnualReportService(test_db)

    with pytest.raises(AppError):
        service.create_report(c.id, 2026, "bad", 1, "A")
    with pytest.raises(AppError):
        service.create_report(c.id, 2026, "corporation", 1, "A", deadline_type="bad")

    service.create_report(c.id, 2026, "corporation", 1, "A")
    with pytest.raises(ConflictError):
        service.create_report(c.id, 2026, "corporation", 1, "A")


def test_create_report_custom_deadline_and_assigned_to_validation(test_db):
    c = _client(test_db, "B")
    service = AnnualReportService(test_db)
    report = service.create_report(
        business_id=c.id,
        tax_year=2025,
        client_type="corporation",
        created_by=1,
        created_by_name="A",
        deadline_type="custom",
    )
    assert report.filing_deadline is None

    with pytest.raises(Exception):
        service.create_report(
            business_id=c.id,
            tax_year=2024,
            client_type="corporation",
            created_by=1,
            created_by_name="A",
            assigned_to=999999,
        )


def test_readiness_incomplete_required_schedule_issue_present(test_db):
    c = _client(test_db, "C")
    service = AnnualReportService(test_db)
    financial = AnnualReportFinancialService(test_db)
    report = service.create_report(c.id, 2026, "corporation", 1, "A", has_rental_income=True)

    # required schedule exists and incomplete -> explicit issue
    readiness = financial.get_readiness_check(report.id)
    assert any("נספח נדרש לא הושלם" in issue for issue in readiness.issues)
    assert readiness.is_ready is False


def test_tax_calculation_uses_detail_credit_components(monkeypatch, test_db):
    c = _client(test_db, "D")
    service = AnnualReportService(test_db)
    financial = AnnualReportFinancialService(test_db)
    report = service.create_report(c.id, 2026, "corporation", 1, "A")

    # ensure summary has taxable income
    financial.add_income(report.id, "salary", 1000)
    detail_repo = financial.detail_repo
    detail_repo.upsert(
        report.id,
        credit_points=2.0,
        pension_credit_points=0.25,
        life_insurance_credit_points=0.5,
        tuition_credit_points=0.25,
        pension_contribution=100.0,
        donation_amount=50.0,
        other_credits=20.0,
    )

    monkeypatch.setattr(financial.vat_repo, "sum_net_vat_by_business_year", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(financial.advance_repo, "sum_paid_by_business_year", lambda *args, **kwargs: 0.0)
    out = financial.get_tax_calculation(report.id)
    assert out.total_credit_points == 3.0
