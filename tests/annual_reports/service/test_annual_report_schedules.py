from tests.annual_reports.service.test_annual_report_enums import AnnualReportSchedule
from tests.annual_reports.service.test_annual_report import AnnualReportService


def test_no_flags_no_schedules():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    assert len(service.get_schedules(report.id)) == 0


def test_self_employed_gets_schedule_a_even_without_flags():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "self_employed", 1, "Advisor")
    schedules = [s.schedule for s in service.get_schedules(report.id)]
    assert schedules == [AnnualReportSchedule.SCHEDULE_A]


def test_rental_income_creates_schedule_b():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    schedules = [s.schedule for s in service.get_schedules(report.id)]
    assert AnnualReportSchedule.SCHEDULE_B in schedules


def test_capital_gains_creates_schedule_gimmel():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", has_capital_gains=True)
    schedules = [s.schedule for s in service.get_schedules(report.id)]
    assert AnnualReportSchedule.SCHEDULE_GIMMEL in schedules


def test_multiple_flags_multiple_schedules():
    service = AnnualReportService()
    report = service.create_report(
        1,
        2023,
        "individual",
        1,
        "Advisor",
        has_rental_income=True,
        has_capital_gains=True,
        has_foreign_income=True,
    )
    schedules = [s.schedule for s in service.get_schedules(report.id)]
    assert AnnualReportSchedule.SCHEDULE_B in schedules
    assert AnnualReportSchedule.SCHEDULE_GIMMEL in schedules
    assert AnnualReportSchedule.SCHEDULE_DALET in schedules
    assert len(schedules) == 3


def test_all_flags_all_schedules():
    service = AnnualReportService()
    report = service.create_report(
        1,
        2023,
        "individual",
        1,
        "Advisor",
        has_rental_income=True,
        has_capital_gains=True,
        has_foreign_income=True,
        has_depreciation=True,
    )
    assert len(service.get_schedules(report.id)) == 3


def test_schedules_start_incomplete():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    schedules = service.get_schedules(report.id)
    assert all(not s.is_complete for s in schedules)


def test_complete_schedule_marks_complete():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    service.complete_schedule(report.id, "schedule_b")
    schedules = service.get_schedules(report.id)
    assert all(s.is_complete for s in schedules)
    assert service.schedules_complete(report.id)


def test_schedules_not_complete_until_all_done():
    service = AnnualReportService()
    report = service.create_report(
        1,
        2023,
        "individual",
        1,
        "Advisor",
        has_rental_income=True,
        has_capital_gains=True,
    )
    service.complete_schedule(report.id, "schedule_b")
    assert not service.schedules_complete(report.id)
    service.complete_schedule(report.id, "schedule_gimmel")
    assert service.schedules_complete(report.id)
