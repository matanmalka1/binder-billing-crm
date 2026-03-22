from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.annual_reports.services import annual_report_pdf_service as pdf_mod
from app.core.exceptions import NotFoundError


def test_fmt_and_r_helpers():
    assert pdf_mod._fmt(None) == "—"
    assert pdf_mod._fmt(1234.5).startswith("₪")
    assert isinstance(pdf_mod._r("שלום"), str)


def test_get_font_falls_back_to_helvetica(monkeypatch):
    monkeypatch.setattr(pdf_mod.os.path, "exists", lambda _p: False)
    assert pdf_mod._get_font() == "Helvetica"


def test_generate_raises_not_found_when_report_missing(test_db):
    service = pdf_mod.AnnualReportPdfService(test_db)

    with pytest.raises(NotFoundError):
        service.generate(999999)


def test_generate_uses_dependencies_and_returns_pdf_bytes(test_db, monkeypatch):
    fake_report = SimpleNamespace(id=7, business_id=10, tax_year=2026, client_type="corporation", status=SimpleNamespace(value="not_started"), ita_reference=None)

    class _Repo:
        def __init__(self, db):
            self.db = db

        def get_by_id(self, report_id):
            return fake_report if report_id == 7 else None

    class _ClientRepo:
        def __init__(self, db):
            self.db = db

        def get_by_id(self, client_id):
            return SimpleNamespace(full_name="Client PDF")

    class _FinSvc:
        def __init__(self, db):
            self.db = db

        def get_financial_summary(self, report_id):
            return SimpleNamespace(
                income_lines=[SimpleNamespace(source_type="salary", amount=1000)],
                expense_lines=[SimpleNamespace(category="other", recognized_amount=100)],
                total_income=1000,
                recognized_expenses=100,
            )

        def get_tax_calculation(self, report_id):
            return SimpleNamespace(
                taxable_income=900,
                pension_deduction=0,
                tax_before_credits=100,
                credit_points_value=20,
                donation_credit=0,
                other_credits=0,
                tax_after_credits=80,
                effective_rate=8.9,
                total_liability=120,
                national_insurance=SimpleNamespace(base_amount=10, high_amount=5, total=15),
            )

    class _DetailSvc:
        def __init__(self, db):
            self.db = db

        def get_detail(self, report_id):
            return SimpleNamespace(tax_refund_amount=Decimal("0"), tax_due_amount=Decimal("120"))

    monkeypatch.setattr(pdf_mod, "AnnualReportRepository", _Repo)
    monkeypatch.setattr(pdf_mod, "ClientRepository", _ClientRepo)
    monkeypatch.setattr(pdf_mod, "AnnualReportFinancialService", _FinSvc)
    monkeypatch.setattr(pdf_mod, "AnnualReportDetailService", _DetailSvc)
    monkeypatch.setattr(pdf_mod, "_build_pdf", lambda *args, **kwargs: b"pdf-bytes")

    payload, tax_year = pdf_mod.AnnualReportPdfService(test_db).generate(7)

    assert payload == b"pdf-bytes"
    assert tax_year == 2026


def test_build_pdf_runs_when_reportlab_available_or_raises():
    report = SimpleNamespace(
        tax_year=2026,
        client_type="corporation",
        status=SimpleNamespace(value="not_started"),
        ita_reference="123",
    )
    summary = SimpleNamespace(
        income_lines=[SimpleNamespace(source_type="salary", amount=1000)],
        expense_lines=[SimpleNamespace(category="other", recognized_amount=100)],
        total_income=1000,
        recognized_expenses=100,
    )
    tax = SimpleNamespace(
        taxable_income=900,
        pension_deduction=0,
        tax_before_credits=100,
        credit_points_value=20,
        donation_credit=0,
        other_credits=0,
        tax_after_credits=80,
        effective_rate=8.9,
        total_liability=120,
        national_insurance=SimpleNamespace(base_amount=10, high_amount=5, total=15),
    )
    detail = SimpleNamespace(tax_refund_amount=0, tax_due_amount=120)

    try:
        pdf = pdf_mod._build_pdf(report, "Client", summary, tax, detail)
        assert isinstance(pdf, (bytes, bytearray))
        assert len(pdf) > 0
    except ImportError:
        pytest.skip("reportlab is not installed in this environment")
