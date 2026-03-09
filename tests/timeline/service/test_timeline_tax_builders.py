from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
)
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.timeline.services.timeline_tax_builders import (
    annual_report_status_changed_event,
    tax_deadline_due_event,
)


def test_tax_deadline_due_event_formats_description_and_amount():
    deadline = SimpleNamespace(
        id=7,
        deadline_type=DeadlineType.VAT,
        due_date=date(2026, 2, 28),
        payment_amount=Decimal("321.50"),
    )

    event = tax_deadline_due_event(deadline)

    assert event["event_type"] == "tax_deadline_due"
    assert event["timestamp"] == datetime(2026, 2, 28)
    assert event["description"] == "מועד מע״מ: 28/02/2026 — ₪321.50"
    assert event["metadata"] == {"tax_deadline_id": 7}
    assert event["actions"] == event["available_actions"] == []


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
    assert event["actions"] == event["available_actions"] == []


def test_tax_deadline_due_event_without_amount_skips_currency_suffix():
    deadline = SimpleNamespace(
        id=8,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date(2026, 3, 31),
        payment_amount=None,
    )

    event = tax_deadline_due_event(deadline)

    assert event["description"] == "מועד דוח שנתי: 31/03/2026"
    assert event["actions"] == event["available_actions"] == []
