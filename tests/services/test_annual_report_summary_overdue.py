from tests.services.annual_report_service import AnnualReportService


def test_season_summary_counts():
    service = AnnualReportService()
    service.create_report(1, 2023, "individual", 1, "A")
    r2 = service.create_report(2, 2023, "corporation", 1, "A")
    service.create_report(3, 2023, "self_employed", 1, "A")
    for status in ["collecting_docs", "docs_complete", "in_preparation", "pending_client", "submitted"]:
        service.transition_status(r2.id, status, 1, "A")
    summary = service.get_season_summary(2023)
    assert summary["total"] == 3
    assert summary["submitted"] == 1
    assert summary["not_started"] == 2


def test_season_summary_years_isolated():
    service = AnnualReportService()
    service.create_report(1, 2022, "individual", 1, "A")
    service.create_report(1, 2023, "individual", 1, "A")
    assert service.get_season_summary(2022)["total"] == 1
    assert service.get_season_summary(2023)["total"] == 1


def test_past_deadline_is_overdue():
    service = AnnualReportService()
    report = service.create_report(1, 2020, "individual", 1, "A", deadline_type="standard")
    overdue = service.get_overdue()
    assert any(o.id == report.id for o in overdue)


def test_submitted_not_overdue():
    service = AnnualReportService()
    report = service.create_report(1, 2020, "individual", 1, "A")
    for status in ["collecting_docs", "docs_complete", "in_preparation", "pending_client", "submitted"]:
        service.transition_status(report.id, status, 1, "A")
    overdue = service.get_overdue()
    assert not any(o.id == report.id for o in overdue)


def test_future_deadline_not_overdue():
    service = AnnualReportService()
    report = service.create_report(1, 2099, "individual", 1, "A", deadline_type="standard")
    overdue = service.get_overdue(tax_year=2099)
    assert not any(o.id == report.id for o in overdue)
