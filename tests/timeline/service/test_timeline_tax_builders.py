from datetime import datetime
from types import SimpleNamespace

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
)
from app.timeline.services.timeline_tax_builders import annual_report_status_changed_event


def test_annual_report_status_changed_event_includes_form_and_status_hebrew():
    report = SimpleNamespace(
        id=3,
        form_type=AnnualReportForm.FORM_1301,
        tax_year=2024,
        status=AnnualReportStatus.COLLECTING_DOCS,
        updated_at=datetime(2026, 1, 1, 12, 0),
    )

    event = annual_report_status_changed_event(report)

    assert event["event_type"] == "annual_report_status_changed"
    assert event["timestamp"] == datetime(2026, 1, 1, 12, 0)
    assert event["description"] == "דוח שנתי 1301 (2024): איסוף מסמכים"
    assert event["metadata"] == {"annual_report_id": 3}
    assert "actions" not in event
    assert event["available_actions"] == []
