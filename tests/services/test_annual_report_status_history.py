import pytest

from app.core.exceptions import AppError
from tests.services.annual_report_enums import AnnualReportStatus
from tests.services.annual_report_service import AnnualReportService


def _full_pipeline(service, client_id=1):
    report = service.create_report(client_id, 2023, "individual", 1, "Advisor")
    service.transition_status(report.id, "collecting_docs", 1, "Advisor")
    service.transition_status(report.id, "docs_complete", 1, "Advisor")
    service.transition_status(report.id, "in_preparation", 1, "Advisor")
    service.transition_status(report.id, "pending_client", 1, "Advisor")
    service.transition_status(report.id, "submitted", 1, "Advisor")
    service.transition_status(report.id, "accepted", 1, "Advisor")
    service.transition_status(report.id, "closed", 1, "Advisor")
    return report


def test_full_happy_path_closes_report():
    service = AnnualReportService()
    report = _full_pipeline(service)
    final = service.get_report(report.id)
    assert final.status == AnnualReportStatus.CLOSED


def test_invalid_skip_rejected():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    with pytest.raises(AppError) as exc_info:
        service.transition_status(report.id, "submitted", 1, "Advisor")
    assert exc_info.value.code == "ANNUAL_REPORT.INVALID_STATUS"


def test_cannot_reopen_closed():
    service = AnnualReportService()
    report = _full_pipeline(service)
    with pytest.raises(AppError) as exc_info:
        service.transition_status(report.id, "collecting_docs", 1, "Advisor")
    assert exc_info.value.code == "ANNUAL_REPORT.INVALID_STATUS"


def test_assessment_then_objection():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    for status in ["collecting_docs", "docs_complete", "in_preparation", "pending_client", "submitted"]:
        service.transition_status(report.id, status, 1, "A")
    service.transition_status(report.id, "assessment_issued", 1, "A", assessment_amount=50000)
    service.transition_status(report.id, "objection_filed", 1, "A")
    service.transition_status(report.id, "closed", 1, "A")
    assert service.get_report(report.id).status == AnnualReportStatus.CLOSED


def test_backward_transition_allowed():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    service.transition_status(report.id, "collecting_docs", 1, "Advisor")
    service.transition_status(report.id, "not_started", 1, "Advisor")
    assert service.get_report(report.id).status == AnnualReportStatus.NOT_STARTED


def test_history_recorded():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    service.transition_status(report.id, "collecting_docs", 1, "Advisor", note="Started collection")
    history = service.get_status_history(report.id)
    assert len(history) == 2
    assert history[-1].to_status == AnnualReportStatus.COLLECTING_DOCS
    assert history[-1].note == "Started collection"


def test_history_first_entry_from_none():
    service = AnnualReportService()
    report = service.create_report(1, 2023, "individual", 1, "Advisor")
    history = service.get_status_history(report.id)
    assert history[0].from_status is None
    assert history[0].to_status == AnnualReportStatus.NOT_STARTED
