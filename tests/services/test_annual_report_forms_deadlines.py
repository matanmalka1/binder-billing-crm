import pytest

from app.core.exceptions import AppError, ConflictError
from tests.services.annual_report_enums import AnnualReportForm, DeadlineType
from tests.services.annual_report_service import AnnualReportService


def test_individual_gets_1301():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1301


def test_self_employed_gets_1215():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "self_employed", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1215


def test_partnership_gets_1215():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "partnership", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1215


def test_corporation_gets_6111():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "corporation", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_6111


def test_invalid_client_type_raises():
    service = AnnualReportService()
    with pytest.raises(AppError) as exc_info:
        service.create_report(1, 2023, "alien", 1, "Advisor")
    assert exc_info.value.code == "ANNUAL_REPORT.INVALID_TYPE"


def test_standard_deadline():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="standard")
    assert report.filing_deadline.year == 2024 and report.filing_deadline.month == 4 and report.filing_deadline.day == 30


def test_extended_deadline():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="extended")
    assert report.filing_deadline.year == 2025 and report.filing_deadline.month == 1 and report.filing_deadline.day == 31


def test_custom_deadline_none():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="custom")
    assert report.filing_deadline is None


def test_extended_later_than_standard():
    service = AnnualReportService()
    std = service.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="standard")
    ext = service.create_report(2, 2023, "individual", 1, "Advisor", deadline_type="extended")
    assert ext.filing_deadline > std.filing_deadline


def test_duplicate_same_client_year():
    service = AnnualReportService()
    service.create_report(1, 2023, "individual", 1, "Advisor")
    with pytest.raises(ConflictError) as exc_info:
        service.create_report(1, 2023, "individual", 1, "Advisor")
    assert exc_info.value.code == "ANNUAL_REPORT.CONFLICT"


def test_same_client_different_years_ok():
    service = AnnualReportService()
    first = service.create_report(1, 2022, "individual", 1, "Advisor")
    second = service.create_report(1, 2023, "individual", 1, "Advisor")
    assert first.id != second.id


def test_different_clients_same_year_ok():
    service = AnnualReportService()
    first = service.create_report(1, 2023, "individual", 1, "Advisor")
    second = service.create_report(2, 2023, "individual", 1, "Advisor")
    assert first.id != second.id
