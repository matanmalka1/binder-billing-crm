import pytest

from app.core.exceptions import AppError, ConflictError
from tests.annual_reports.service.test_annual_report_enums import AnnualReportForm, AnnualReportSchedule, DeadlineType
from tests.annual_reports.service.test_annual_report import AnnualReportService


def test_individual_gets_1301():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1301


def test_self_employed_gets_1301():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "self_employed", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1301


def test_partnership_gets_1301():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "partnership", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1301


def test_corporation_gets_1214():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "corporation", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1214


def test_public_institution_gets_1215():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "public_institution", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1215


def test_exempt_dealer_gets_1301_in_main_annual_report_flow():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "exempt_dealer", 1, "Advisor")
    assert report.form_type == AnnualReportForm.FORM_1301


def test_partnership_auto_generates_form_1504_schedule():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "partnership", 1, "Advisor")
    schedules = {entry.schedule for entry in service.get_schedules(report.id)}
    assert AnnualReportSchedule.SCHEDULE_A in schedules
    assert AnnualReportSchedule.FORM_1504 in schedules


def test_invalid_client_type_raises():
    service = AnnualReportService()
    with pytest.raises(AppError) as exc_info:
        service.create_report(1, 2023, "alien", 1, "Advisor")
    assert exc_info.value.code == "ANNUAL_REPORT.INVALID_TYPE"


def test_standard_deadline():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="standard")
    assert report.filing_deadline.year == 2024 and report.filing_deadline.month == 5 and report.filing_deadline.day == 29


def test_standard_deadline_online_individual():
    service = AnnualReportService()
    report = service.create_report(
        1, 2023, "individual", 1, "Advisor",
        deadline_type="standard", submission_method="online",
    )
    assert report.filing_deadline.year == 2024 and report.filing_deadline.month == 6 and report.filing_deadline.day == 30


def test_standard_deadline_corporation():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "corporation", 1, "Advisor", deadline_type="standard")
    assert report.filing_deadline.year == 2024 and report.filing_deadline.month == 7 and report.filing_deadline.day == 31


def test_standard_deadline_public_institution():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "public_institution", 1, "Advisor", deadline_type="standard")
    assert report.filing_deadline.year == 2024 and report.filing_deadline.month == 7 and report.filing_deadline.day == 31


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


def test_duplicate_same_client_year_different_profile_still_conflicts():
    service = AnnualReportService()
    service.create_report(1, 2023, "individual", 1, "Advisor")
    with pytest.raises(ConflictError) as exc_info:
        service.create_report(1, 2023, "self_employed", 1, "Advisor")
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
