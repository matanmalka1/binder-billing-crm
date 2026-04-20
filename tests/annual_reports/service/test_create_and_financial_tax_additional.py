from datetime import date
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_credit_point_reason import (
    AnnualReportCreditPoint,
    CreditPointReason,
)
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
        client_record_id=c.id,
        tax_year=2025,
        client_type="corporation",
        created_by=1,
        created_by_name="A",
        deadline_type="custom",
    )
    assert report.filing_deadline is None

    with pytest.raises(Exception):
        service.create_report(
            client_record_id=c.id,
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
    financial.detail_repo.update_meta(
        report.id,
        pension_contribution=100.0,
        donation_amount=50.0,
        other_credits=20.0,
    )
    test_db.add_all([
        AnnualReportCreditPoint(
            annual_report_id=report.id,
            reason=CreditPointReason.RESIDENT,
            points=2.0,
        ),
        AnnualReportCreditPoint(
            annual_report_id=report.id,
            reason=CreditPointReason.ACADEMIC_DEGREE,
            points=1.0,
        ),
    ])
    test_db.flush()

    monkeypatch.setattr(financial.vat_repo, "sum_net_vat_by_client_record_year", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(financial.advance_repo, "sum_paid_by_client_year", lambda *args, **kwargs: 0.0)
    out = financial.get_tax_calculation(report.id)
    assert out.total_credit_points == 3.0


def test_income_line_allows_zero_amount(test_db):
    c = _client(test_db, "E")
    service = AnnualReportService(test_db)
    financial = AnnualReportFinancialService(test_db)
    report = service.create_report(c.id, 2026, "corporation", 1, "A")

    line = financial.add_income(report.id, "salary", 0)

    assert float(line.amount) == 0.0
    summary = financial.get_financial_summary(report.id)
    assert float(summary.total_income) == 0.0


def test_expense_line_uses_external_document_reference(test_db):
    c = _client(test_db, "F")
    service = AnnualReportService(test_db)
    financial = AnnualReportFinancialService(test_db)
    report = service.create_report(c.id, 2026, "corporation", 1, "A")

    line = financial.add_expense(
        report.id,
        "office_rent",
        250,
        external_document_reference="INV-2026-001",
    )

    assert line.external_document_reference == "INV-2026-001"
    assert line.supporting_document_id is None


def test_annex_line_creates_schedule_owner_when_missing(test_db):
    c = _client(test_db, "G")
    service = AnnualReportService(test_db)
    report = service.create_report(c.id, 2026, "corporation", 1, "A")

    assert service.get_annex_lines(report.id, AnnualReportSchedule.SCHEDULE_B) == []

    line = service.add_annex_line(
        report.id,
        AnnualReportSchedule.SCHEDULE_B,
        {"rental_income": 12000},
        notes="auto owner",
    )

    assert line.schedule == AnnualReportSchedule.SCHEDULE_B
    assert line.annual_report_id == report.id
    schedules = service.get_schedules(report.id)
    assert any(
        entry.schedule == AnnualReportSchedule.SCHEDULE_B and entry.is_required is False
        for entry in schedules
    )
